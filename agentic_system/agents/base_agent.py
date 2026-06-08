"""
agents/base_agent.py
─────────────────────────────────────────────────────────────────────────────
Base agent class — provides:
  • MCP client connections to all three servers
  • Task queue interaction (claim / complete / fail)
  • Health logging
  • Self-healing circuit breaker via tenacity
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import json
import asyncio
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tenacity import (
    AsyncRetrying, stop_after_attempt, wait_exponential,
    RetryError, before_sleep_log,
)
from loguru import logger
import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import get_pool
from config import get_settings

settings = get_settings()

# ── Paths to each MCP server script ──────────────────────────────────────────
_SERVERS_DIR = Path(__file__).resolve().parent.parent / "mcp_servers"
ATS_SERVER  = str(_SERVERS_DIR / "ats_mcp_server.py")
VMS_SERVER  = str(_SERVERS_DIR / "vms_mcp_server.py")
COMM_SERVER = str(_SERVERS_DIR / "comm_mcp_server.py")


class BaseAgent(ABC):
    """
    Abstract base for all placement agents.
    Sub-classes implement `run_task(task_id, payload)`.
    """

    name: str = "base-agent"

    # ── MCP sessions (lazy-initialized) ──────────────────────────────────────
    _ats_session:  ClientSession | None = None
    _vms_session:  ClientSession | None = None
    _comm_session: ClientSession | None = None

    async def _call_tool(self, session: ClientSession, tool: str, **kwargs) -> dict | list:
        """Call an MCP tool and return its result dict or list."""
        list_tools = {"fetch_new_requisitions", "semantic_search_candidates", "list_candidates"}
        
        result = await session.call_tool(tool, arguments=kwargs)
        if result.content and len(result.content) > 0:
            raw = result.content[0].text
            try:
                parsed = json.loads(raw)
                # FastMCP sometimes unpacks single-item lists into a raw dict
                if tool in list_tools and isinstance(parsed, dict):
                    return [parsed]
                return parsed
            except Exception:
                return {"raw": raw}
        
        # If successful but empty, return [] for list-returning tools, else {}
        if tool in list_tools:
            return []
        return {}

    # ── Convenience wrappers ──────────────────────────────────────────────────

    async def call_ats(self, tool: str, **kwargs) -> dict:
        return await self._call_tool(self._ats_session, tool, **kwargs)

    async def call_vms(self, tool: str, **kwargs) -> dict:
        return await self._call_tool(self._vms_session, tool, **kwargs)

    async def call_comm(self, tool: str, **kwargs) -> dict:
        return await self._call_tool(self._comm_session, tool, **kwargs)

    # ── Task queue ────────────────────────────────────────────────────────────

    async def claim_next_task(self, task_type: str) -> dict | None:
        """Atomically claim the next pending task of this type."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE agent_task_queue
                SET status = 'running',
                    assigned_agent = $1,
                    attempts = attempts + 1,
                    updated_at = NOW()
                WHERE id = (
                    SELECT id FROM agent_task_queue
                    WHERE status = 'pending'
                      AND task_type = $2
                      AND scheduled_at <= NOW()
                    ORDER BY scheduled_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, task_type, payload, attempts, max_attempts
                """,
                self.name, task_type,
            )
        if row:
            payload = row["payload"]
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception as e:
                    logger.error(f"Failed to parse task payload JSON: {e}")
            return {"id": str(row["id"]), "task_type": row["task_type"],
                    "payload": payload, "attempts": row["attempts"],
                    "max_attempts": row["max_attempts"]}
        return None

    async def complete_task(self, task_id: str) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE agent_task_queue SET status='done', updated_at=NOW() WHERE id=$1",
                task_id,
            )
        await self._log_health("task_completed", f"Task {task_id} done.")

    async def fail_task(self, task_id: str, error: str, attempts: int, max_attempts: int) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            if attempts >= max_attempts:
                new_status = "human_review"
                # Mark as __alerted__ immediately so self-healing never sends
                # repeat emails for the same task
                logger.warning(f"[{self.name}] Task {task_id} → HUMAN REVIEW after {attempts} attempts.")
                await self._log_health("circuit_open", f"Circuit open on task {task_id}: {error}")
                await conn.execute(
                    "UPDATE agent_task_queue SET status=$1, last_error=$2, assigned_agent='__alerted__', updated_at=NOW() WHERE id=$3",
                    new_status, error, task_id,
                )
            else:
                await conn.execute(
                    "UPDATE agent_task_queue SET status='pending', last_error=$1, updated_at=NOW() WHERE id=$2",
                    error, task_id,
                )

    async def enqueue_task(
        self, task_type: str, payload: dict,
        delay_seconds: int = 0, max_attempts: int = 3,
    ) -> str:
        pool = await get_pool()
        from datetime import timedelta
        scheduled_at = datetime.utcnow()
        if delay_seconds:
            scheduled_at += timedelta(seconds=delay_seconds)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO agent_task_queue
                  (task_type, payload, status, max_attempts, scheduled_at)
                VALUES ($1, $2, 'pending', $3, $4)
                RETURNING id
                """,
                task_type, json.dumps(payload), max_attempts, scheduled_at,
            )
        return str(row["id"])

    # ── Health logging ────────────────────────────────────────────────────────

    async def _log_health(self, event_type: str, message: str, metadata: dict | None = None) -> None:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO agent_health_log (agent_name, event_type, message, metadata)
                    VALUES ($1, $2, $3, $4)
                    """,
                    self.name, event_type, message,
                    json.dumps(metadata) if metadata else None,
                )
        except Exception:
            pass  # Don't let health logging kill the agent

    # ── Abstract ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def run_task(self, task_id: str, payload: dict) -> None:
        """Process a single task. Implementations must call complete_task or fail_task."""
        ...

    async def run_loop(self, task_type: str, poll_interval: int = 5) -> None:
        """Main polling loop — runs forever, picks up tasks from the queue."""
        await self._log_health("started", f"{self.name} loop started.")
        logger.info(f"[{self.name}] Watching for '{task_type}' tasks every {poll_interval}s.")
        while True:
            try:
                task = await self.claim_next_task(task_type)
                if task:
                    logger.info(f"[{self.name}] Claimed task {task['id']} (attempt {task['attempts']}/{task['max_attempts']})")
                    try:
                        async for attempt in AsyncRetrying(
                            stop=stop_after_attempt(1),  # inner retries handled at task level
                            wait=wait_exponential(min=2, max=30),
                            reraise=True,
                        ):
                            with attempt:
                                await self.run_task(task["id"], task["payload"])
                    except Exception as exc:
                        err_msg = str(exc)
                        if hasattr(exc, "exceptions") and exc.exceptions:
                            err_msg = f"{err_msg} (Underlying: {'; '.join(str(e) for e in exc.exceptions)})"
                        await self.fail_task(task["id"], err_msg, task["attempts"], task["max_attempts"])
                        await self._log_health("failed", err_msg)
                else:
                    await asyncio.sleep(poll_interval)
            except Exception as exc:
                logger.error(f"[{self.name}] Loop error: {exc}")
                await asyncio.sleep(10)
