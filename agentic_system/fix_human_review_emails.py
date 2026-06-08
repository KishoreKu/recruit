"""
One-shot script: marks all existing human_review tasks as __alerted__
so the self-healing agent immediately stops sending repeat emails.
Run from the agentic_system directory with the venv active.
"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import get_pool

async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE agent_task_queue
            SET assigned_agent = '__alerted__'
            WHERE status = 'human_review'
              AND (assigned_agent IS NULL OR assigned_agent != '__alerted__')
            """
        )
    count = int(result.split(" ")[-1])
    print(f"✅ Marked {count} human_review tasks as alerted. Emails will stop after next agent cycle (~60s).")
    await pool.close()

asyncio.run(main())
