"""
agents/client_outreach_agent.py
─────────────────────────────────────────────────────────────────────────────
Client Outreach Agent — "The Business Developer"
Handles client_speculation tasks:
  1. Claims client_speculation tasks.
  2. Fetches candidate profile from ATS MCP and job details from VMS MCP.
  3. Uses Gemini to draft a personalized spec-pitch email to the hiring manager.
  4. Calls the send_email tool on the comm_mcp_server to send the spec-pitch.
  5. Completes the task and logs the event in outreach_log.
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


class ClientOutreachAgent(BaseAgent):
    name = "client-outreach-agent"

    async def run_task(self, task_id: str, payload: dict) -> None:
        """
        Process a 'client_speculation' task.
        Payload: { requisition_id, candidate_id, client_contact_name, client_contact_email }
        """
        required = ["requisition_id", "candidate_id", "client_contact_email"]
        missing = [f for f in required if not payload.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        requisition_id = payload["requisition_id"]
        candidate_id = payload["candidate_id"]
        client_contact_name = payload.get("client_contact_name") or "Hiring Manager"
        client_contact_email = payload["client_contact_email"]

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

                                # 1. Fetch full candidate profile
                                candidate = await self.call_ats("get_candidate", candidate_id=candidate_id)
                                if "error" in candidate:
                                    raise RuntimeError(f"Candidate not found: {candidate_id}")

                                # 2. Fetch full requisition details
                                req = await self.call_vms("get_requisition", requisition_id=requisition_id)
                                if "error" in req:
                                    raise RuntimeError(f"Requisition not found: {requisition_id}")

                                # 3. Generate personalized pitch using Gemini
                                prompt = f"""
                                You are a senior business development director at Westley Resource, a premier IT staffing agency.
                                Draft a highly tailored, compelling, and professional speculative sales email to a client contact to pitch a top-matched candidate.
                                
                                CLIENT DETAILS:
                                Contact Name: {client_contact_name}
                                Contact Email: {client_contact_email}
                                Client Company: {req.get('client_company', 'their company')}
                                
                                ROLE DETAILS:
                                Job Title: {req['title']}
                                Skills Required: {', '.join(req.get('skills_required', []))}
                                Description/Context: {req.get('description', '')[:1000]}
                                
                                CANDIDATE DETAILS:
                                Name: {candidate['full_name']}
                                Current Title: {candidate.get('current_title', 'Specialist')}
                                Current Company: {candidate.get('current_company', 'N/A')}
                                Experience Years: {candidate.get('experience_years', 'N/A')}
                                Skills: {', '.join(candidate.get('skills', []))}
                                Resume: {candidate.get('resume_raw', '')[:2000]}
                                
                                EMAIL REQUIREMENTS:
                                1. Personalization: Address {client_contact_name} directly and refer to their open {req['title']} position.
                                2. Value Pitch: Summarize the candidate's background, highlight how their skills map to the job's key needs, and list 2-3 specific accomplishments (based on candidate resume) showing how they deliver results.
                                3. Professionalism: Do not include candidate contact details or bill rates in the initial pitch. Keep candidate contact information confidential.
                                4. Call to Action: Request a 10-minute introductory call to discuss the candidate or how Westley Resource can support their staffing needs under a Master Services Agreement (MSA).
                                5. Output Format: Return a single JSON object with two fields:
                                   - "subject": A compelling subject line (e.g. "Top Candidate Pitch: {req['title']} - {candidate['full_name']}")
                                   - "body_html": The complete email body formatted in clean, modern HTML (use `<p>`, `<strong>`, `<ul>`, `<li>` tags). No generic placeholders. Sign off as the "Westley Resource Team".
                                
                                Output ONLY valid JSON. Do not include markdown block markers like ```json.
                                """
                                
                                logger.info(f"[Client Outreach Agent] Drafting spec pitch for {client_contact_email} (Candidate: {candidate['full_name']})")
                                res_text = await chat_completion(prompt, system="You are an expert sales writer and JSON parser. Output only valid JSON.")
                                res_text = res_text.strip().removeprefix("```json").removesuffix("```").strip()
                                
                                try:
                                    data = json.loads(res_text)
                                    subject = data["subject"]
                                    body_html = data["body_html"]
                                except Exception as e:
                                    logger.error(f"[Client Outreach Agent] Failed to parse generated pitch JSON: {e}. Raw response: {res_text}")
                                    # Fallback simple pitch
                                    subject = f"Introductory candidate pitch for open {req['title']} role"
                                    body_html = f"""
                                    <p>Dear {client_contact_name},</p>
                                    <p>I hope this email finds you well.</p>
                                    <p>I noticed your opening for a <strong>{req['title']}</strong>. We have a highly qualified candidate, <strong>{candidate['full_name']}</strong>, who is a strong fit for this position with extensive experience in {', '.join(candidate.get('skills', [])[:5])}.</p>
                                    <p>I would love to set up a quick 10-minute call to discuss how we can assist your team under a Master Services Agreement (MSA).</p>
                                    <p>Best regards,<br>Westley Resource Team</p>
                                    """

                                # 4. Send email
                                email_result = await self.call_comm(
                                    "send_email",
                                    to_address=client_contact_email,
                                    subject=subject,
                                    body_html=body_html,
                                    candidate_id=candidate_id,
                                )

                                if email_result.get("status") == "failed":
                                    raise RuntimeError(f"Email delivery failed: {email_result.get('error')}")

                                logger.success(f"[Client Outreach Agent] ✅ Outreach email sent to {client_contact_email} pitching {candidate['full_name']}")
                                await self.complete_task(task_id)
                                await self._log_health("succeeded", f"Sent speculation pitch to {client_contact_email} for candidate {candidate_id}")


async def main():
    agent = ClientOutreachAgent()
    await agent.run_loop(task_type="client_speculation", poll_interval=5)


if __name__ == "__main__":
    asyncio.run(main())
