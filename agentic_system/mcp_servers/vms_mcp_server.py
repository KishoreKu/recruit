"""
mcp_servers/vms_mcp_server.py
─────────────────────────────────────────────────────────────────────────────
VMS (Vendor Management System) MCP Server.

In production this connects to real VMS platforms (SAP Fieldglass, Beeline,
Workday Contingent Workforce, Ariba, Coupa, etc.) via their APIs or Playwright
browser automation.

For now it provides:
  • fetch_new_requisitions()        — poll for open jobs
  • submit_candidate(...)           — submit a candidate to a VMS job
  • check_submission_status(id)     — poll for interview / offer updates
  • add_requisition(...)            — manual / demo mode: add a test job
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import json
import asyncio
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from loguru import logger
from db import get_pool
from gemini_client import embed_text, chat_completion
from config import get_settings

settings = get_settings()
mcp = FastMCP("vms-mcp-server")


# ─── Tool: fetch_new_requisitions ─────────────────────────────────────────────

@mcp.tool()
async def fetch_new_requisitions(limit: int = 50) -> list[dict]:
    """
    1. Scrape live job sources (Adzuna, JSearch, USAJobs) for new IT jobs.
    2. Insert any genuinely new jobs into the requisitions table.
    3. Return all currently open requisitions for matching.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from job_scrapers import scrape_all_sources

    pool = await get_pool()

    # ── Step 1: Scrape live sources ───────────────────────────────────────────
    try:
        listings = await scrape_all_sources()
        logger.info(f"[VMS] Scraped {len(listings)} listings from live sources.")
    except Exception as e:
        logger.error(f"[VMS] Scraping failed, falling back to DB only: {e}")
        listings = []

    # ── Step 2: Insert new jobs (skip duplicates by external_id) ─────────────
    new_count = 0
    for listing in listings:
        if not listing.title or not listing.client_company:
            continue
        try:
            # Check for duplicate by external_id or title+company
            async with pool.acquire() as conn:
                exists = await conn.fetchval(
                    """
                    SELECT 1 FROM requisitions
                    WHERE (vms_job_id = $1 AND vms_platform = $2)
                       OR (title = $3 AND client_company = $4)
                    LIMIT 1
                    """,
                    listing.external_id or None,
                    listing.vms_platform,
                    listing.title,
                    listing.client_company,
                )
                if exists:
                    continue

                # Embed the job for semantic matching
                embedding = await embed_text(f"{listing.title}\n{listing.description}")

                await conn.execute(
                    """
                    INSERT INTO requisitions
                      (vms_platform, vms_job_id, title, client_company, skills_required,
                       location, job_type, bill_rate_max, description, embedding, status)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,'open')
                    ON CONFLICT DO NOTHING
                    """,
                    listing.vms_platform,
                    listing.external_id or None,
                    listing.title,
                    listing.client_company,
                    listing.skills_required,
                    listing.location,
                    listing.job_type,
                    listing.bill_rate_max,
                    listing.description[:3000],
                    embedding,
                )
                new_count += 1
        except Exception as e:
            logger.warning(f"[VMS] Failed to insert '{listing.title}': {e}")

    if new_count:
        logger.success(f"[VMS] Inserted {new_count} new requisitions from live scraping.")

    # ── Step 3: Return all open requisitions ──────────────────────────────────
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, vms_platform, vms_job_id, title, client_company,
                   skills_required, location, job_type, bill_rate_max,
                   description, status, deadline, created_at
            FROM requisitions
            WHERE status = 'open'
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )

    results = []
    for row in rows:
        r = dict(row)
        r["id"] = str(r["id"])
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
        if r.get("deadline"):
            r["deadline"] = r["deadline"].isoformat()
        results.append(r)

    logger.info(f"[VMS] Returning {len(results)} open requisitions ({new_count} newly scraped).")
    return results


# ─── Tool: submit_candidate ───────────────────────────────────────────────────

@mcp.tool()
async def submit_candidate(
    requisition_id: str,
    candidate_id: str,
    bill_rate: float,
    notes: str | None = None,
) -> dict:
    """
    Submit a candidate to a VMS requisition.
    In production: POST to VMS platform API with formatted profile.
    Returns a submission_id for status tracking.
    """
    pool = await get_pool()

    # Verify requisition exists
    async with pool.acquire() as conn:
        req = await conn.fetchrow(
            "SELECT id, title, vms_platform, vms_job_id FROM requisitions WHERE id = $1",
            requisition_id,
        )
        if not req:
            return {"error": f"Requisition {requisition_id} not found."}

        cand = await conn.fetchrow(
            "SELECT id, full_name, email, rtr_given FROM candidates WHERE id = $1",
            candidate_id,
        )
        if not cand:
            return {"error": f"Candidate {candidate_id} not found."}

        if not cand["rtr_given"]:
            return {
                "error": "RTR_MISSING",
                "message": f"Candidate {cand['full_name']} has not given Right-To-Represent consent.",
                "candidate_id": candidate_id,
            }

    # ── In production: POST to real VMS API here ──────────────
    # E.g. for Fieldglass:
    #   resp = await http_client.post(FIELDGLASS_URL, json={...})
    #   vms_submission_id = resp.json()["submissionId"]
    # ─────────────────────────────────────────────────────────
    vms_submission_id = f"WR-{uuid.uuid4().hex[:8].upper()}"

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO submissions
              (candidate_id, requisition_id, vms_submission_id, bill_rate_submitted, notes, status)
            VALUES ($1, $2, $3, $4, $5, 'submitted')
            ON CONFLICT (candidate_id, requisition_id)
              DO UPDATE SET
                vms_submission_id = EXCLUDED.vms_submission_id,
                bill_rate_submitted = EXCLUDED.bill_rate_submitted,
                status = 'submitted',
                submitted_at = NOW()
            RETURNING id, status, submitted_at
            """,
            candidate_id, requisition_id, vms_submission_id, bill_rate, notes,
        )

    result = {
        "submission_id": str(row["id"]),
        "vms_submission_id": vms_submission_id,
        "status": row["status"],
        "submitted_at": row["submitted_at"].isoformat(),
        "candidate": cand["full_name"],
        "requisition": req["title"],
        "vms_platform": req["vms_platform"],
    }
    logger.success(f"[VMS] Submitted {cand['full_name']} → {req['title']} ({vms_submission_id})")
    return result


# ─── Tool: check_submission_status ───────────────────────────────────────────

@mcp.tool()
async def check_submission_status(submission_id: str) -> dict:
    """
    Check the current status of a candidate submission.
    In production, polls the VMS platform API.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT s.id, s.vms_submission_id, s.status, s.bill_rate_submitted,
                   s.submitted_at, s.updated_at, s.notes,
                   c.full_name AS candidate_name, c.email AS candidate_email,
                   r.title AS job_title, r.vms_platform
            FROM submissions s
            JOIN candidates c ON c.id = s.candidate_id
            JOIN requisitions r ON r.id = s.requisition_id
            WHERE s.id = $1
            """,
            submission_id,
        )
    if not row:
        return {"error": f"Submission {submission_id} not found."}

    r = dict(row)
    r["id"] = str(r["id"])
    r["submitted_at"] = r["submitted_at"].isoformat()
    r["updated_at"] = r["updated_at"].isoformat()
    return r


# ─── Tool: add_requisition (for manual testing / demo) ───────────────────────

@mcp.tool()
async def add_requisition(
    title: str,
    client_company: str,
    description: str,
    skills_required: list[str],
    location: str,
    job_type: str = "Contract",
    bill_rate_max: float | None = None,
    vms_platform: str = "manual",
    deadline_iso: str | None = None,
) -> dict:
    """
    Manually add a requisition to the system (demo / testing / scraping result).
    In production, VMS polling fills this automatically.
    """
    embedding = await embed_text(f"{title}\n{description}")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO requisitions
              (vms_platform, title, client_company, skills_required, location,
               job_type, bill_rate_max, description, embedding, deadline)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING id, title, status, created_at
            """,
            vms_platform, title, client_company, skills_required, location,
            job_type, bill_rate_max, description, embedding,
            datetime.fromisoformat(deadline_iso) if deadline_iso else None,
        )
    r = dict(row)
    r["id"] = str(r["id"])
    r["created_at"] = r["created_at"].isoformat()
    logger.success(f"[VMS] Requisition added: {title}")
    return r


if __name__ == "__main__":
    logger.info("Starting VMS MCP Server...")
    mcp.run(transport="stdio")
