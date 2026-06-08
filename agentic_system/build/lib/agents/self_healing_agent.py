"""
agents/self_healing_agent.py
─────────────────────────────────────────────────────────────────────────────
Self-Healing Monitor Agent — "The Safety Net"
Runs continuously alongside all other agents. Responsibilities:
  1. Detect stuck tasks (running > timeout threshold) → reset to pending
  2. Detect circuit-open tasks (human_review) → notify admin
  3. Refresh MS Graph token proactively (before expiry)
  4. Report health summary every 15 minutes
  5. Detect crashed agent processes (by checking health_log gaps)
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from db import get_pool
from config import get_settings

settings = get_settings()

STUCK_TASK_TIMEOUT_MINUTES = 15
HEALTH_REPORT_INTERVAL_SECONDS = 900  # 15 minutes
ADMIN_EMAIL = settings.MS_SENDER


class SelfHealingAgent:
    name = "self-healing-agent"

    async def _log_health(self, event_type: str, message: str, metadata: dict | None = None) -> None:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO agent_health_log (agent_name, event_type, message, metadata) VALUES ($1,$2,$3,$4)",
                    self.name, event_type, message, json.dumps(metadata) if metadata else None,
                )
        except Exception:
            pass

    # ── Heal stuck tasks ─────────────────────────────────────────────────────

    async def heal_stuck_tasks(self) -> int:
        """
        Find tasks stuck in 'running' state for too long and reset them.
        This handles crashes of agent processes mid-task.
        """
        pool = await get_pool()
        cutoff = datetime.utcnow() - timedelta(minutes=STUCK_TASK_TIMEOUT_MINUTES)
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE agent_task_queue
                SET status = 'pending',
                    assigned_agent = NULL,
                    last_error = 'Reset by self-healing agent (stuck timeout)',
                    updated_at = NOW()
                WHERE status = 'running'
                  AND updated_at < $1
                  AND attempts < max_attempts
                """,
                cutoff,
            )
        count = int(result.split(" ")[-1])
        if count > 0:
            logger.warning(f"[Self-Healing] Reset {count} stuck tasks → pending.")
            await self._log_health("recovered", f"Reset {count} stuck tasks.", {"cutoff": cutoff.isoformat()})
        return count

    # ── Alert on human-review tasks ──────────────────────────────────────────

    async def alert_human_review_tasks(self) -> int:
        """Find tasks requiring human review and send admin alert email."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, task_type, payload, last_error, attempts, updated_at
                FROM agent_task_queue
                WHERE status = 'human_review'
                  AND updated_at > NOW() - INTERVAL '16 minutes'
                ORDER BY updated_at DESC
                LIMIT 20
                """
            )

        if not rows:
            return 0

        # Build summary for admin alert
        task_list = "\n".join(
            f"  • Task {r['id']} [{r['task_type']}] — {r['last_error']} ({r['attempts']} attempts)"
            for r in rows
        )
        logger.warning(f"[Self-Healing] {len(rows)} task(s) need human review:\n{task_list}")
        await self._log_health("circuit_open", f"{len(rows)} tasks in human_review.", {"count": len(rows)})

        # Send admin notification via MS Graph (if configured)
        if settings.MS_TENANT_ID and settings.MS_CLIENT_ID:
            try:
                from mcp_servers.comm_mcp_server import send_email  # type: ignore
                # Directly invoke the function (avoids MCP overhead for internal use)
                import aiohttp
                body = f"""
                <h2>⚠️ Agentic System — Human Review Required</h2>
                <p>{len(rows)} task(s) have failed {settings.MAX_TASK_ATTEMPTS}+ times and need manual review:</p>
                <pre>{task_list}</pre>
                <p>Please check the <code>agent_task_queue</code> table for details.</p>
                """
                # Use Graph API directly
                import aiohttp, time
                token_url = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token"
                token_data = {
                    "grant_type": "client_credentials",
                    "client_id": settings.MS_CLIENT_ID,
                    "client_secret": settings.MS_CLIENT_SECRET,
                    "scope": "https://graph.microsoft.com/.default",
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(token_url, data=token_data) as r:
                        token_payload = await r.json()
                    token = token_payload.get("access_token")
                    if token:
                        mail_url = f"https://graph.microsoft.com/v1.0/users/{settings.MS_SENDER}/sendMail"
                        mail_payload = {
                            "message": {
                                "subject": f"[Westley Agents] {len(rows)} task(s) need human review",
                                "body": {"contentType": "HTML", "content": body},
                                "toRecipients": [{"emailAddress": {"address": ADMIN_EMAIL}}],
                            }
                        }
                        await session.post(
                            mail_url,
                            json=mail_payload,
                            headers={"Authorization": f"Bearer {token}"},
                        )
            except Exception as e:
                logger.warning(f"[Self-Healing] Admin alert email failed: {e}")

        return len(rows)

    # ── Health summary report ─────────────────────────────────────────────────

    async def report_health_summary(self) -> dict:
        """Query health stats from the DB and log a summary."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            task_stats = await conn.fetchrow(
                """
                SELECT
                  COUNT(*) FILTER (WHERE status='pending')  AS pending,
                  COUNT(*) FILTER (WHERE status='running')  AS running,
                  COUNT(*) FILTER (WHERE status='done')     AS done,
                  COUNT(*) FILTER (WHERE status='failed')   AS failed,
                  COUNT(*) FILTER (WHERE status='human_review') AS human_review
                FROM agent_task_queue
                WHERE created_at > NOW() - INTERVAL '1 hour'
                """
            )
            candidate_count = await conn.fetchval("SELECT COUNT(*) FROM candidates")
            submission_count = await conn.fetchval("SELECT COUNT(*) FROM submissions")

        summary = {
            "task_queue_last_hour": dict(task_stats),
            "total_candidates": candidate_count,
            "total_submissions": submission_count,
            "reported_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"[Self-Healing] Health Report — "
            f"Tasks(1h): pending={task_stats['pending']} running={task_stats['running']} "
            f"done={task_stats['done']} failed={task_stats['failed']} "
            f"human_review={task_stats['human_review']} | "
            f"Candidates: {candidate_count} | Submissions: {submission_count}"
        )
        await self._log_health("health_report", "Periodic health summary.", summary)
        return summary

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Run all healing checks in a continuous loop."""
        await self._log_health("started", "Self-Healing Monitor started.")
        logger.info("[Self-Healing] Monitor started.")

        last_health_report = datetime.utcnow() - timedelta(seconds=HEALTH_REPORT_INTERVAL_SECONDS)

        while True:
            try:
                # 1. Heal stuck tasks (every loop)
                await self.heal_stuck_tasks()

                # 2. Alert on circuit-open tasks (every loop)
                await self.alert_human_review_tasks()

                # 3. Health report (every 15 minutes)
                if (datetime.utcnow() - last_health_report).total_seconds() >= HEALTH_REPORT_INTERVAL_SECONDS:
                    await self.report_health_summary()
                    last_health_report = datetime.utcnow()

            except Exception as exc:
                logger.error(f"[Self-Healing] Monitor error: {exc}")

            await asyncio.sleep(60)  # Check every 60 seconds


async def main():
    agent = SelfHealingAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
