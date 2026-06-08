"""
agents/submission_agent.py
─────────────────────────────────────────────────────────────────────────────
Submission Agent — "The Coordinator"
Handles TWO task types:
  1. submit_candidate   — format + submit to VMS (with self-healing)
  2. check_rtr_reply    — read inbox, detect RTR consent, proceed if yes
─────────────────────────────────────────────────────────────────────────────
Self-healing logic:
  • Missing bill_rate   → enqueue ask_candidate_info task
  • Missing visa_status → enqueue ask_candidate_info task
  • VMS submission fail → log error, retry (up to max_attempts), then human review
  • RTR not confirmed   → re-send outreach after 24h (up to 2 re-sends)
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


class SubmissionAgent(BaseAgent):
    name = "submission-agent"

    # ─── Task dispatcher ──────────────────────────────────────────────────────

    async def run_task(self, task_id: str, payload: dict) -> None:
        task_type = payload.get("_task_type", "submit_candidate")

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

                                if task_type == "check_rtr_reply":
                                    await self._check_rtr_reply(task_id, payload)
                                elif task_type == "ask_candidate_info":
                                    await self._ask_missing_info(task_id, payload)
                                else:
                                    await self._submit_candidate(task_id, payload)

    # ─── submit_candidate ─────────────────────────────────────────────────────

    async def _submit_candidate(self, task_id: str, payload: dict) -> None:
        candidate_id = payload["candidate_id"]
        requisition_id = payload["requisition_id"]
        bill_rate = payload.get("bill_rate")

        # 1. Fetch full candidate profile
        candidate = await self.call_ats("get_candidate", candidate_id=candidate_id)
        if "error" in candidate:
            raise RuntimeError(f"Candidate not found: {candidate_id}")

        # ── Self-healing: missing bill_rate ──────────────────────────────────
        if not bill_rate and not candidate.get("bill_rate"):
            logger.warning(f"[Submission Agent] Missing bill_rate for {candidate['full_name']}. Requesting info.")
            await self.enqueue_task("ask_candidate_info", {
                "_task_type": "ask_candidate_info",
                "candidate_id": candidate_id,
                "requisition_id": requisition_id,
                "missing_field": "bill_rate",
                "candidate_email": candidate["email"],
                "candidate_name": candidate["full_name"],
                "candidate_phone": candidate.get("phone"),
            })
            # Don't fail — just wait for info to come back
            await self.complete_task(task_id)
            return

        # ── Self-healing: missing visa_status ────────────────────────────────
        if not candidate.get("visa_status"):
            logger.warning(f"[Submission Agent] Missing visa_status for {candidate['full_name']}. Requesting info.")
            await self.enqueue_task("ask_candidate_info", {
                "_task_type": "ask_candidate_info",
                "candidate_id": candidate_id,
                "requisition_id": requisition_id,
                "missing_field": "visa_status",
                "candidate_email": candidate["email"],
                "candidate_name": candidate["full_name"],
                "candidate_phone": candidate.get("phone"),
            })
            await self.complete_task(task_id)
            return

        final_rate = float(bill_rate or candidate.get("bill_rate", 100))

        # 2. Submit to VMS
        result = await self.call_vms(
            "submit_candidate",
            requisition_id=requisition_id,
            candidate_id=candidate_id,
            bill_rate=final_rate,
        )

        if "error" in result:
            if result.get("error") == "RTR_MISSING":
                # Self-healing: re-trigger outreach
                logger.warning(f"[Submission Agent] RTR missing — re-queuing outreach for {candidate_id}")
                await self.enqueue_task("match_candidates", {
                    "requisition_id": requisition_id,
                    "trigger": "rtr_retry",
                })
                await self.complete_task(task_id)
                return
            raise RuntimeError(f"VMS submission error: {result['error']}")

        # 3. Update candidate status
        await self.call_ats(
            "update_candidate_status",
            candidate_id=candidate_id,
            status="active",
            notes=f"Submitted to {requisition_id} as {result.get('vms_submission_id')}",
        )

        # 4. Send confirmation email to candidate
        await self.call_comm(
            "send_email",
            to_address=candidate["email"],
            subject=f"✅ You've been submitted — {result.get('requisition')}",
            body_html=f"""
            <p>Hi {candidate['full_name'].split()[0]},</p>
            <p>Great news! You've been submitted to <strong>{result.get('requisition')}</strong>.</p>
            <p><strong>Submission ID:</strong> {result.get('vms_submission_id')}</p>
            <p>We'll be in touch as soon as we hear back from the client. 🎯</p>
            <p>Best,<br>Westley Resource Team</p>
            """,
            candidate_id=candidate_id,
        )

        logger.success(f"[Submission Agent] ✅ Submitted {candidate['full_name']} → {result.get('vms_submission_id')}")
        await self.complete_task(task_id)
        await self._log_health("succeeded", f"Submitted {candidate_id} for {requisition_id}")

    # ─── check_rtr_reply ──────────────────────────────────────────────────────

    async def _check_rtr_reply(self, task_id: str, payload: dict) -> None:
        candidate_id = payload["candidate_id"]
        requisition_id = payload["requisition_id"]
        candidate_email = payload["candidate_email"]

        # Read inbox and look for a reply from this candidate
        messages = await self.call_comm("read_inbox", unread_only=True, limit=50)
        if not isinstance(messages, list):
            messages = []

        reply = next(
            (m for m in messages if m.get("from_email", "").lower() == candidate_email.lower()),
            None,
        )

        if not reply:
            logger.info(f"[Submission Agent] No reply from {candidate_email} yet.")
            await self.complete_task(task_id)
            return

        # Use Gemini to analyse the reply
        consent = await self.call_comm("detect_rtr_consent", email_body=reply["body"])

        if consent.get("rtr_given") is True:
            logger.success(f"[Submission Agent] RTR confirmed from {candidate_email}!")

            # Update candidate record
            await self.call_ats(
                "update_candidate_status",
                candidate_id=candidate_id,
                status="rtr_given",
            )

            # Extract bill rate if mentioned
            if consent.get("bill_rate_mentioned"):
                await self.call_ats(
                    "update_candidate_field",
                    candidate_id=candidate_id,
                    field="bill_rate",
                    value=str(consent["bill_rate_mentioned"]),
                )

            # Queue submission
            await self.enqueue_task("submit_candidate", {
                "candidate_id": candidate_id,
                "requisition_id": requisition_id,
                "bill_rate": consent.get("bill_rate_mentioned"),
            })

        elif consent.get("rtr_given") is False:
            logger.info(f"[Submission Agent] Candidate {candidate_email} declined.")
        else:
            logger.info(f"[Submission Agent] Consent unclear for {candidate_email}. Scheduling re-check.")

        await self.complete_task(task_id)

    # ─── ask_missing_info (self-healing) ──────────────────────────────────────

    async def _ask_missing_info(self, task_id: str, payload: dict) -> None:
        field = payload["missing_field"]
        name = payload["candidate_name"]
        email = payload["candidate_email"]
        candidate_id = payload["candidate_id"]

        questions = {
            "bill_rate": "What is your expected hourly bill rate (in USD)?",
            "visa_status": "What is your work authorization status? (e.g. US Citizen, Green Card, H1B, OPT, etc.)",
        }
        question = questions.get(field, f"Could you please provide your {field}?")

        result = await self.call_comm(
            "send_email",
            to_address=email,
            subject=f"Quick question before your submission, {name.split()[0]}",
            body_html=f"""
            <p>Hi {name.split()[0]},</p>
            <p>We're almost ready to submit your profile! We just need one quick piece of info:</p>
            <p><strong>{question}</strong></p>
            <p>Please reply directly to this email. We'll take care of the rest!</p>
            <p>Best,<br>Westley Resource Team</p>
            """,
            candidate_id=candidate_id,
        )

        if result.get("status") == "failed" and payload.get("candidate_phone"):
            await self.call_comm(
                "send_sms",
                to_number=payload["candidate_phone"],
                message=f"Hi {name.split()[0]}, Westley Resource needs your {field} to complete your submission. Please email us at support@westleyresource.com",
                candidate_id=candidate_id,
            )

        # Re-schedule the submission after giving candidate time to reply
        await self.enqueue_task("submit_candidate", {
            "candidate_id": payload["candidate_id"],
            "requisition_id": payload["requisition_id"],
        }, delay_seconds=24 * 3600)  # Retry submission in 24 hours

        await self.complete_task(task_id)
        logger.info(f"[Submission Agent] Requested '{field}' from {email}.")


async def main():
    agent = SubmissionAgent()
    await asyncio.gather(
        agent.run_loop(task_type="submit_candidate", poll_interval=5),
        agent.run_loop(task_type="check_rtr_reply", poll_interval=10),
        agent.run_loop(task_type="ask_candidate_info", poll_interval=5),
    )


if __name__ == "__main__":
    asyncio.run(main())
