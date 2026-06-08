"""
agents/ats_agent.py
─────────────────────────────────────────────────────────────────────────────
ATS Agent — "The Recruiter"
Handles: ingest_resume tasks
  1. Receives resume text (from email / upload webhook)
  2. Calls ATS MCP → add_candidate (Gemini parses + embeds)
  3. Schedules a match_candidates task for the Matching Agent
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from loguru import logger
from agents.base_agent import BaseAgent, ATS_SERVER, VMS_SERVER, COMM_SERVER


class ATSAgent(BaseAgent):
    name = "ats-agent"

    async def run_task(self, task_id: str, payload: dict) -> None:
        """
        Process an 'ingest_resume' task.
        Payload: { full_name, email, phone?, resume_text }
        """
        required = ["full_name", "email", "resume_text"]
        missing = [f for f in required if not payload.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        async with stdio_client(StdioServerParameters(command="python", args=[ATS_SERVER])) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                self._ats_session = session

                result = await self.call_ats(
                    "add_candidate",
                    full_name=payload["full_name"],
                    email=payload["email"],
                    phone=payload.get("phone"),
                    resume_text=payload["resume_text"],
                )

        if "error" in result:
            raise RuntimeError(f"ATS add_candidate failed: {result['error']}")

        candidate_id = result["id"]
        logger.success(f"[ATS Agent] Candidate ingested: {candidate_id} ({payload['email']})")

        # Schedule matching for all open requisitions
        await self.enqueue_task("match_candidates", {
            "candidate_id": candidate_id,
            "trigger": "new_candidate",
        })

        await self.complete_task(task_id)
        await self._log_health("succeeded", f"Ingested candidate {candidate_id}")


async def main():
    agent = ATSAgent()
    await agent.run_loop(task_type="ingest_resume", poll_interval=5)


if __name__ == "__main__":
    asyncio.run(main())
