"""
agents/matching_agent.py
─────────────────────────────────────────────────────────────────────────────
Matching & Outreach Agent — "The Sourcer"
Handles: match_candidates tasks
  1. Given a requisition_id, calls VMS MCP → get_requisition (direct DB)
  2. Calls ATS MCP → semantic_search_candidates
  3. Scores each match with Gemini reasoning
  4. Sends personalized RTR outreach via Comm MCP
  5. Schedules rtr_check tasks (watches inbox for replies)
─────────────────────────────────────────────────────────────────────────────
Fix (2026-06-08): Replaced fetch_new_requisitions (full scrape + embed of all
jobs) with get_requisition (single DB row lookup). The old call was triggering
the job scraper + Gemini embed for every match task, which timed out inside
the MCP stdio subprocess and caused Python 3.11 anyio TaskGroup to raise an
ExceptionGroup — landing every match task in human_review.
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from loguru import logger
from agents.base_agent import BaseAgent, ATS_SERVER, VMS_SERVER, COMM_SERVER
from gemini_client import chat_completion
from config import get_settings

settings = get_settings()


def _build_rtr_email(
    candidate_name: str,
    job_title: str,
    client_company: str,
    location: str,
    job_type: str,
    similarity_score: float,
) -> tuple[str, str]:
    """Build a personalized RTR outreach email (subject + HTML body)."""
    subject = f"Exciting {job_type} Opportunity — {job_title} at {client_company}"
    body = f"""
    <p>Hi {candidate_name.split()[0]},</p>
    <p>Hope you're doing well! I came across an exciting opportunity that seems like a strong match for your background:</p>
    <ul>
      <li><strong>Role:</strong> {job_title}</li>
      <li><strong>Client:</strong> {client_company}</li>
      <li><strong>Location:</strong> {location}</li>
      <li><strong>Type:</strong> {job_type}</li>
    </ul>
    <p>Based on your profile, this looks like an excellent fit (match score: {round(similarity_score * 100)}%).</p>
    <p><strong>To proceed, we need your Right-To-Represent (RTR) consent.</strong>
    Please simply reply <strong>"Yes, please submit me"</strong> (or similar) to this email,
    along with your expected hourly bill rate if not already on file.</p>
    <p>Feel free to ask any questions — happy to provide more details.</p>
    <p>Best regards,<br>
    <strong>Westley Resource Recruiting Team</strong><br>
    <a href="mailto:support@westleyresource.com">support@westleyresource.com</a></p>
    """
    return subject, body


class MatchingAgent(BaseAgent):
    name = "matching-agent"

    async def run_task(self, task_id: str, payload: dict) -> None:
        """
        Process a 'match_candidates' task.
        Payload: { requisition_id?, candidate_id?, trigger }
        """
        requisition_id = payload.get("requisition_id")
        candidate_id = payload.get("candidate_id")

        import os
        async with stdio_client(StdioServerParameters(command="python", args=[ATS_SERVER], env=dict(os.environ))) as (ra, wa):
            async with ClientSession(ra, wa) as ats:
                await ats.initialize()
                self._ats_session = ats

                async with stdio_client(StdioServerParameters(command="python", args=[VMS_SERVER], env=dict(os.environ))) as (rv, wv):
                    async with ClientSession(rv, wv) as vms:
                        await vms.initialize()
                        self._vms_session = vms

                        async with stdio_client(StdioServerParameters(command="python", args=[COMM_SERVER], env=dict(os.environ))) as (rc, wc):
                            async with ClientSession(rc, wc) as comm:
                                await comm.initialize()
                                self._comm_session = comm

                                await self._process_matching(
                                    task_id, payload,
                                    requisition_id, candidate_id
                                )

    async def _process_matching(self, task_id, payload, requisition_id, candidate_id):
        """Core matching logic (called inside MCP session context)."""

        if requisition_id:
            # Job-triggered: find best candidates for this job
            await self._match_job_to_candidates(task_id, requisition_id)
        elif candidate_id:
            # Candidate-triggered: find best jobs for this candidate
            await self._match_candidate_to_jobs(task_id, candidate_id)
        else:
            raise ValueError("match_candidates task requires requisition_id or candidate_id.")

    async def _match_job_to_candidates(self, task_id: str, requisition_id: str):
        """Find top candidates for a given job and send RTR outreach."""

        # 1. Get requisition details — use direct DB lookup, NOT fetch_new_requisitions.
        #    fetch_new_requisitions triggers a full job scrape + embed for all jobs on
        #    every call, which times out inside the MCP subprocess and crashes the TaskGroup.
        req = await self.call_vms("get_requisition", requisition_id=requisition_id)
        if not req or "error" in req:
            raise RuntimeError(f"Requisition {requisition_id} not found: {req.get('error', 'unknown')}")

        job_desc = f"{req['title']}\n{req.get('description', '')}\nSkills: {', '.join(req.get('skills_required', []))}"

        # 2. Semantic search for top K matching candidates
        matches = await self.call_ats(
            "semantic_search_candidates",
            job_description=job_desc,
            top_k=settings.MATCH_TOP_K,
            status_filter="active",
        )

        if not matches or isinstance(matches, dict):
            logger.info(f"[Matching Agent] No candidates matched for {requisition_id}.")
            await self.complete_task(task_id)
            return

        logger.info(f"[Matching Agent] Found {len(matches)} candidates for '{req['title']}'.")

        # 3. Ask Gemini to rank and filter the matches
        ranking_prompt = f"""
        You are a senior IT recruiter. Evaluate these {len(matches)} candidates for this role:

        JOB: {req['title']} at {req.get('client_company', 'Client')}
        DESCRIPTION: {req.get('description', '')[:500]}
        REQUIRED SKILLS: {', '.join(req.get('skills_required', []))}

        CANDIDATES (JSON):
        {json.dumps([{
            'id': c['id'],
            'name': c['full_name'],
            'title': c['current_title'],
            'skills': c['skills'],
            'experience_years': c['experience_years'],
            'similarity_score': c['similarity_score'],
        } for c in matches], indent=2)}

        Return a JSON array of candidate IDs to pursue (max 3), in priority order.
        Only include strong matches. Format: {{"selected": ["id1", "id2"]}}
        """
        raw = await chat_completion(ranking_prompt)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            selection = json.loads(raw)
            selected_ids = set(selection.get("selected", []))
        except Exception:
            # Fallback: take top 3 by similarity score
            selected_ids = {m["id"] for m in matches[:3]}

        # 4. Send RTR outreach to selected candidates
        for candidate in matches:
            if candidate["id"] not in selected_ids:
                continue
            if candidate.get("rtr_given"):
                # Already has RTR — skip to submission
                await self.enqueue_task("submit_candidate", {
                    "candidate_id": candidate["id"],
                    "requisition_id": requisition_id,
                    "bill_rate": candidate.get("bill_rate") or req.get("bill_rate_max", 100),
                })
                continue

            subject, body = _build_rtr_email(
                candidate_name=candidate["full_name"],
                job_title=req["title"],
                client_company=req.get("client_company", "Our Client"),
                location=req.get("location", "TBD"),
                job_type=req.get("job_type", "Contract"),
                similarity_score=candidate["similarity_score"],
            )

            email_result = await self.call_comm(
                "send_email",
                to_address=candidate["email"],
                subject=subject,
                body_html=body,
                candidate_id=candidate["id"],
            )

            if email_result.get("status") == "failed" and email_result.get("suggest_fallback") == "sms":
                if candidate.get("phone"):
                    logger.warning(f"[Matching Agent] Email failed, falling back to SMS for {candidate['email']}")
                    await self.call_comm(
                        "send_sms",
                        to_number=candidate["phone"],
                        message=f"Hi {candidate['full_name'].split()[0]}, Westley Resource has a great {req['title']} role. Reply YES to be submitted. Email: support@westleyresource.com",
                        candidate_id=candidate["id"],
                    )

            # Schedule RTR reply check immediately (Option A: continuous polling)
            await self.enqueue_task("check_rtr_reply", {
                "candidate_id": candidate["id"],
                "requisition_id": requisition_id,
                "candidate_email": candidate["email"],
            })

        await self.complete_task(task_id)
        await self._log_health("succeeded", f"Matched {len(selected_ids)} candidates for {requisition_id}")

    async def _match_candidate_to_jobs(self, task_id: str, candidate_id: str):
        """When a new candidate is ingested, find best jobs for them."""
        candidate = await self.call_ats("get_candidate", candidate_id=candidate_id)
        if not candidate or "error" in candidate:
            raise RuntimeError(candidate.get("error", f"Candidate {candidate_id} not found"))

        skills_text = ", ".join(candidate.get("skills", []))
        logger.info(f"[Matching Agent] Finding jobs for candidate {candidate_id} ({candidate.get('full_name')}).")

        # Fetch open requisitions directly from DB (no scraping) — just get IDs to queue.
        # We use the pool directly here to avoid triggering the full VMS scrape.
        from db import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id FROM requisitions WHERE status = 'open' ORDER BY created_at DESC LIMIT 20"
            )
        requisition_ids = [str(r["id"]) for r in rows]
        logger.info(f"[Matching Agent] Queuing {len(requisition_ids)} job→candidate match tasks.")

        # For each open job, queue a job→candidate match task
        for req_id in requisition_ids:
            await self.enqueue_task("match_candidates", {
                "requisition_id": req_id,
                "trigger": "new_candidate_check",
            })

        await self.complete_task(task_id)


async def main():
    agent = MatchingAgent()
    await agent.run_loop(task_type="match_candidates", poll_interval=5)


if __name__ == "__main__":
    asyncio.run(main())
