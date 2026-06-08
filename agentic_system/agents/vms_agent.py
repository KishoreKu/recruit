"""
agents/vms_agent.py
─────────────────────────────────────────────────────────────────────────────
VMS Agent — "The Account Manager"
Handles: periodic VMS polling for new job requisitions.
  1. Every N minutes, calls VMS MCP → fetch_new_requisitions()
  2. For any truly new jobs (not already in DB), schedules match_candidates tasks
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from loguru import logger
from agents.base_agent import BaseAgent, VMS_SERVER
from config import get_settings

settings = get_settings()


class VMSAgent(BaseAgent):
    name = "vms-agent"

    async def run_task(self, task_id: str, payload: dict) -> None:
        """Process a 'poll_vms' task — fetch new requisitions."""
        import os
        async with stdio_client(StdioServerParameters(command="python", args=[VMS_SERVER], env=dict(os.environ))) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                self._vms_session = session

                requisitions = await self.call_vms("fetch_new_requisitions", limit=20)

        if not isinstance(requisitions, list):
            raise RuntimeError(f"VMS fetch failed: {requisitions}")

        new_count = 0
        for req in requisitions:
            # Schedule matching for each open requisition
            await self.enqueue_task("match_candidates", {
                "requisition_id": req["id"],
                "trigger": "vms_poll",
                "title": req.get("title"),
            })
            new_count += 1

        logger.info(f"[VMS Agent] Polled {len(requisitions)} requisitions, queued {new_count} matching tasks.")
        await self.complete_task(task_id)
        await self._log_health("succeeded", f"Polled VMS: {new_count} new matches queued.")

    async def run_polling_loop(self) -> None:
        """
        Periodic VMS polling loop — enqueues a poll_vms task every N minutes.
        Runs alongside the task queue loop.
        """
        interval = settings.VMS_POLL_INTERVAL_SECONDS
        logger.info(f"[VMS Agent] Starting polling every {interval}s.")
        while True:
            await self.enqueue_task("poll_vms", {"source": "scheduler"})
            await asyncio.sleep(interval)

    async def run(self) -> None:
        """Run both the polling scheduler and task execution loop concurrently."""
        await asyncio.gather(
            self.run_polling_loop(),
            self.run_loop(task_type="poll_vms", poll_interval=10),
        )


async def main():
    agent = VMSAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
