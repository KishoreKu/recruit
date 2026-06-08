"""
mcp_servers/ats_mcp_server.py
─────────────────────────────────────────────────────────────────────────────
ATS MCP Server — Exposes Applicant Tracking System tools over MCP protocol.

Tools:
  • add_candidate(data)              — parse resume + store with embedding
  • update_candidate_status(id, status)
  • semantic_search_candidates(job_description, top_k)
  • get_candidate(id)
  • list_candidates(status, limit)
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import json
import asyncio
from pathlib import Path

# Ensure parent dir is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from loguru import logger
from db import get_pool
from gemini_client import embed_text, chat_completion
from config import get_settings

settings = get_settings()
mcp = FastMCP("ats-mcp-server")


# ─── Tool: add_candidate ─────────────────────────────────────────────────────

@mcp.tool()
async def add_candidate(
    full_name: str,
    email: str,
    phone: str | None,
    resume_text: str,
) -> dict:
    """
    Parse a candidate's raw resume text with Gemini, generate an embedding,
    and upsert the candidate record into the ATS database.
    """
    logger.info(f"[ATS] Ingesting candidate: {email}")

    # 1. Use Gemini to extract structured data from the raw resume
    extraction_prompt = f"""
    Extract structured candidate information from this resume text.
    Return strictly valid JSON with these fields:
    {{
      "full_name": string,
      "email": string,
      "phone": string or null,
      "skills": [list of skill strings],
      "experience_years": integer or null,
      "current_title": string or null,
      "current_company": string or null,
      "location": string or null,
      "visa_status": string or null
    }}

    Resume:
    {resume_text}

    JSON:
    """
    try:
        raw = await chat_completion(extraction_prompt)
        # Strip markdown fences if any
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(raw)
    except Exception as e:
        logger.warning(f"[ATS] Gemini extraction fallback: {e}")
        parsed = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "skills": [],
            "experience_years": None,
            "current_title": None,
            "current_company": None,
            "location": None,
            "visa_status": None,
        }

    # Override with explicitly passed values
    parsed["full_name"] = full_name or parsed.get("full_name", "")
    parsed["email"] = email
    parsed["phone"] = phone or parsed.get("phone")

    # 2. Generate 768-dim embedding of the resume text
    embedding = await embed_text(resume_text[:8000])  # cap at 8k chars

    # 3. Upsert into Postgres
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO candidates
              (full_name, email, phone, skills, experience_years,
               current_title, current_company, location, visa_status,
               resume_raw, embedding)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (email) DO UPDATE SET
              full_name = EXCLUDED.full_name,
              skills = EXCLUDED.skills,
              experience_years = EXCLUDED.experience_years,
              current_title = EXCLUDED.current_title,
              current_company = EXCLUDED.current_company,
              location = EXCLUDED.location,
              visa_status = EXCLUDED.visa_status,
              resume_raw = EXCLUDED.resume_raw,
              embedding = EXCLUDED.embedding,
              updated_at = NOW()
            RETURNING id, full_name, email, status
            """,
            parsed["full_name"],
            parsed["email"],
            parsed["phone"],
            parsed.get("skills", []),
            parsed.get("experience_years"),
            parsed.get("current_title"),
            parsed.get("current_company"),
            parsed.get("location"),
            parsed.get("visa_status"),
            resume_text,
            embedding,
        )

    result = dict(row)
    result["id"] = str(result["id"])
    logger.success(f"[ATS] Candidate upserted: {result['id']}")
    return result


# ─── Tool: update_candidate_status ───────────────────────────────────────────

@mcp.tool()
async def update_candidate_status(
    candidate_id: str,
    status: str,
    notes: str | None = None,
) -> dict:
    """
    Update a candidate's status: active | placed | inactive | rtr_given.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if status == "rtr_given":
            row = await conn.fetchrow(
                "UPDATE candidates SET rtr_given = TRUE, updated_at = NOW() WHERE id = $1 RETURNING id, email, status",
                candidate_id,
            )
        else:
            row = await conn.fetchrow(
                "UPDATE candidates SET status = $1, updated_at = NOW() WHERE id = $2 RETURNING id, email, status",
                status, candidate_id,
            )
    if not row:
        return {"error": f"Candidate {candidate_id} not found"}
    result = dict(row)
    result["id"] = str(result["id"])
    logger.info(f"[ATS] Updated candidate {candidate_id} → {status}")
    return result


# ─── Tool: semantic_search_candidates ────────────────────────────────────────

@mcp.tool()
async def semantic_search_candidates(
    job_description: str,
    top_k: int = 5,
    status_filter: str = "active",
) -> list[dict]:
    """
    Perform cosine-similarity vector search to find the best matching
    candidates for a given job description. Returns top_k results.
    """
    logger.info(f"[ATS] Semantic search for: {job_description[:80]}...")
    query_embedding = await embed_text(job_description[:8000])

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, full_name, email, phone, skills, experience_years,
                   current_title, current_company, location, visa_status,
                   bill_rate, rtr_given, status,
                   1 - (embedding <=> $1::vector) AS similarity_score
            FROM candidates
            WHERE status = $2
              AND embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            query_embedding,
            status_filter,
            top_k,
        )

    results = []
    for row in rows:
        r = dict(row)
        r["id"] = str(r["id"])
        r["similarity_score"] = round(float(r["similarity_score"]), 4)
        results.append(r)

    logger.info(f"[ATS] Found {len(results)} candidates.")
    return results


# ─── Tool: get_candidate ─────────────────────────────────────────────────────

@mcp.tool()
async def get_candidate(candidate_id: str) -> dict:
    """Fetch full candidate record by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM candidates WHERE id = $1", candidate_id
        )
    if not row:
        return {"error": f"Not found: {candidate_id}"}
    r = dict(row)
    r["id"] = str(r["id"])
    r.pop("embedding", None)  # Don't return raw vector
    return r


# ─── Tool: update_candidate_field ────────────────────────────────────────────

@mcp.tool()
async def update_candidate_field(
    candidate_id: str,
    field: str,
    value: str,
) -> dict:
    """
    Update a single specific field on a candidate record.
    Allowed fields: bill_rate, visa_status, phone, location.
    """
    allowed = {"bill_rate", "visa_status", "phone", "location"}
    if field not in allowed:
        return {"error": f"Field '{field}' not updatable. Allowed: {allowed}"}
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE candidates SET {field} = $1, updated_at = NOW() WHERE id = $2 RETURNING id, email",
            value, candidate_id,
        )
    if not row:
        return {"error": f"Candidate {candidate_id} not found"}
    logger.info(f"[ATS] Updated {field} for candidate {candidate_id}")
    return {"id": str(row["id"]), "email": row["email"], "updated_field": field, "new_value": value}


if __name__ == "__main__":
    logger.info(f"Starting ATS MCP Server on port {settings.ATS_MCP_PORT}...")
    mcp.run(transport="stdio")
