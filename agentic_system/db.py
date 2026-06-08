"""
db.py — Async PostgreSQL connection pool for the agentic system.
Uses asyncpg + pgvector.
"""
import asyncpg
from pgvector.asyncpg import register_vector
from loguru import logger
from config import get_settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return (or create) the shared connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=1,
            max_size=2,
            init=_init_connection,
        )
        logger.info("Database pool initialised.")
    return _pool


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register the pgvector codec on every new connection."""
    await register_vector(conn)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed.")
