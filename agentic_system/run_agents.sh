#!/bin/bash
# ============================================================
#  run_agents.sh — One-command launcher for the entire system
#  Usage: cd agentic_system && ./run_agents.sh
# ============================================================
set -e

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Westley Resource — Agentic Placement System        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Check Python 3.11+ ────────────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Install Python 3.11+."
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PY_VERSION found."

# ── Step 2: Install / sync dependencies with uv ───────────────────────────────
if command -v uv &> /dev/null; then
    echo "📦 Installing dependencies with uv..."
    uv sync
    PYTHON="$(uv run python -c 'import sys; print(sys.executable)')"
else
    echo "⚠️  uv not found, falling back to pip..."
    python3 -m pip install fastapi uvicorn mcp google-generativeai asyncpg \
        pgvector python-dotenv pydantic pydantic-settings loguru tenacity \
        aiohttp apscheduler httpx requests -q
    PYTHON="python3"
fi

echo ""
echo "🗄️  Running database migrations..."
if command -v psql &> /dev/null; then
    # Try to apply schema — will skip if tables already exist
    PGPASSWORD="${PGPASSWORD:-}" psql "${DATABASE_URL:-postgresql://localhost:5432/westleyresource}" \
        -f schema_agents.sql 2>&1 | grep -E "(CREATE|ERROR|already)" || true
    echo "✅ Schema ready."
else
    echo "⚠️  psql not found — run schema_agents.sql manually in your Postgres client."
fi

echo ""
echo "🚀 Starting Orchestrator (all agents)..."
echo "   Dashboard: http://localhost:${ORCHESTRATOR_PORT:-8200}"
echo "   API docs:  http://localhost:${ORCHESTRATOR_PORT:-8200}/docs"
echo ""
echo "   Endpoints:"
echo "   POST /ingest-resume  — add a candidate"
echo "   POST /add-job        — add a VMS job"
echo "   GET  /status         — system health"
echo "   GET  /candidates     — ATS candidates"
echo "   GET  /submissions    — placement tracker"
echo ""

exec $PYTHON -m uvicorn orchestrator:app \
    --host 0.0.0.0 \
    --port "${ORCHESTRATOR_PORT:-8200}" \
    --log-level info
