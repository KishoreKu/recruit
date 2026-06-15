"""
mcp_servers/comm_mcp_server.py
─────────────────────────────────────────────────────────────────────────────
Communication MCP Server — Exposes outreach tools:
  • send_email(...)      — via Microsoft Graph API (your existing mailer)
  • send_sms(...)        — via Twilio (SMS fallback when email bounces)
  • read_inbox(...)      — read MS Outlook inbox for RTR replies
  • log_outreach(...)    — persist all communications to outreach_log table
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import json
import asyncio
import aiohttp
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from loguru import logger
from db import get_pool
from config import get_settings

settings = get_settings()
mcp = FastMCP("comm-mcp-server")

# ─── MS Graph token cache (in-memory, refreshed when expired) ────────────────
_ms_token_cache: dict = {"access_token": None, "expires_at": 0}


async def _get_ms_token() -> str:
    """Fetch or refresh Microsoft Graph Bearer token."""
    import time
    if _ms_token_cache["access_token"] and time.time() < _ms_token_cache["expires_at"] - 60:
        return _ms_token_cache["access_token"]

    url = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.MS_CLIENT_ID,
        "client_secret": settings.MS_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"MS Graph token error {resp.status}: {text}")
            payload = await resp.json()

    import time
    _ms_token_cache["access_token"] = payload["access_token"]
    _ms_token_cache["expires_at"] = time.time() + payload.get("expires_in", 3600)
    logger.info("[COMM] MS Graph token refreshed.")
    return _ms_token_cache["access_token"]


# ─── Tool: send_email ─────────────────────────────────────────────────────────

@mcp.tool()
async def send_email(
    to_address: str,
    subject: str,
    body_html: str,
    candidate_id: str | None = None,
    bypass_review: bool = False,
    outreach_id: str | None = None,
) -> dict:
    """
    Queue an email for Human-In-The-Loop review, or send it directly if bypass_review is True.
    """
    if not bypass_review:
        logger.info(f"[COMM] Intercepting email to {to_address} for human review (HITL).")
        inserted_id = await _log_outreach(
            candidate_id=candidate_id,
            channel="email",
            direction="outbound",
            subject=subject,
            body=body_html,
            status="pending_review",
            metadata={"to_address": to_address}
        )
        return {"status": "pending_review", "to": to_address, "subject": subject, "outreach_id": inserted_id}

    if to_address.endswith(".local") or "candidate.local" in to_address:
        logger.warning(f"[COMM] Intercepted email to placeholder local domain ({to_address}) — email bypassed.")
        await _log_outreach(candidate_id, "email", "outbound", subject, body_html, "bypassed", {"to_address": to_address}, outreach_id=outreach_id)
        return {"status": "simulated", "to": to_address, "subject": subject}

    if not settings.MS_TENANT_ID or not settings.MS_CLIENT_ID:
        logger.warning("[COMM] MS Graph not configured — email simulated.")
        await _log_outreach(candidate_id, "email", "outbound", subject, body_html, "simulated", {"to_address": to_address}, outreach_id=outreach_id)
        return {"status": "simulated", "to": to_address, "subject": subject}

    try:
        token = await _get_ms_token()
        url = f"https://graph.microsoft.com/v1.0/users/{settings.MS_SENDER}/sendMail"
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": to_address}}],
            },
            "saveToSentItems": True,
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status in (200, 202):
                    await _log_outreach(candidate_id, "email", "outbound", subject, body_html, "sent", {"to_address": to_address}, outreach_id=outreach_id)
                    logger.success(f"[COMM] Email sent → {to_address}")
                    return {"status": "sent", "to": to_address, "subject": subject}
                else:
                    text = await resp.text()
                    await _log_outreach(candidate_id, "email", "outbound", subject, body_html, "failed",
                                        {"error": text, "http_status": resp.status, "to_address": to_address}, outreach_id=outreach_id)
                    return {"status": "failed", "error": text, "http_status": resp.status}

    except Exception as exc:
        logger.error(f"[COMM] Email failed: {exc}")
        await _log_outreach(candidate_id, "email", "outbound", subject, body_html, "failed",
                            {"exception": str(exc), "to_address": to_address}, outreach_id=outreach_id)
        # Signal to self-healing agent that we need a fallback channel
        return {"status": "failed", "error": str(exc), "suggest_fallback": "sms"}


# ─── Tool: send_sms ───────────────────────────────────────────────────────────

@mcp.tool()
async def send_sms(
    to_number: str,
    message: str,
    candidate_id: str | None = None,
) -> dict:
    """
    Send an SMS via Twilio. Used as fallback when email bounces.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("[COMM] Twilio not configured — SMS simulated.")
        await _log_outreach(candidate_id, "sms", "outbound", None, message, "simulated")
        return {"status": "simulated", "to": to_number}

    try:
        from twilio.rest import Client  # type: ignore
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_number,
        )
        await _log_outreach(candidate_id, "sms", "outbound", None, message, "sent",
                            {"twilio_sid": msg.sid})
        logger.success(f"[COMM] SMS sent → {to_number} (SID: {msg.sid})")
        return {"status": "sent", "to": to_number, "twilio_sid": msg.sid}

    except Exception as exc:
        logger.error(f"[COMM] SMS failed: {exc}")
        await _log_outreach(candidate_id, "sms", "outbound", None, message, "failed",
                            {"exception": str(exc)})
        return {"status": "failed", "error": str(exc)}


# ─── Tool: read_inbox ─────────────────────────────────────────────────────────

@mcp.tool()
async def read_inbox(
    folder: str = "Inbox",
    unread_only: bool = True,
    limit: int = 20,
) -> list[dict]:
    """
    Read emails from the MS Outlook inbox to detect RTR replies.
    Returns list of messages with sender, subject, body.
    """
    if not settings.MS_TENANT_ID or not settings.MS_CLIENT_ID:
        logger.warning("[COMM] MS Graph not configured — returning empty inbox.")
        return []

    try:
        token = await _get_ms_token()
        filter_param = "isRead eq false" if unread_only else ""
        url = (
            f"https://graph.microsoft.com/v1.0/users/{settings.MS_SENDER}"
            f"/mailFolders/{folder}/messages"
            f"?$top={limit}"
            + (f"&$filter={filter_param}" if filter_param else "")
            + "&$select=id,subject,from,receivedDateTime,bodyPreview,body"
        )
        headers = {"Authorization": f"Bearer {token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"[COMM] Inbox read error: {resp.status}")
                    return []
                data = await resp.json()

        messages = []
        for m in data.get("value", []):
            messages.append({
                "message_id": m["id"],
                "subject": m.get("subject"),
                "from_email": m.get("from", {}).get("emailAddress", {}).get("address"),
                "from_name": m.get("from", {}).get("emailAddress", {}).get("name"),
                "received_at": m.get("receivedDateTime"),
                "body_preview": m.get("bodyPreview"),
                "body": m.get("body", {}).get("content", ""),
            })

        logger.info(f"[COMM] Read {len(messages)} inbox messages.")
        return messages

    except Exception as exc:
        logger.error(f"[COMM] Inbox read failed: {exc}")
        return []


# ─── Tool: detect_rtr_consent ─────────────────────────────────────────────────

@mcp.tool()
async def detect_rtr_consent(email_body: str) -> dict:
    """
    Use Gemini to analyze an email body and determine if the candidate
    gave Right-To-Represent (RTR) consent, extracted any bill rate, etc.
    """
    from gemini_client import chat_completion
    prompt = f"""
    Analyze this email from a job candidate. Determine:
    1. Did they give consent to be submitted/represented? (yes/no/unclear)
    2. Did they mention a bill rate or salary? (extract it or null)
    3. Did they ask a question? (yes/no, and what question if yes)
    4. What is their overall sentiment? (positive/negative/neutral)

    Return strictly valid JSON:
    {{
      "rtr_given": true/false/null,
      "bill_rate_mentioned": number or null,
      "has_question": true/false,
      "question": string or null,
      "sentiment": "positive"/"negative"/"neutral"
    }}

    Email body:
    {email_body[:3000]}

    JSON:
    """
    raw = await chat_completion(prompt)
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"rtr_given": None, "error": "parse_failed", "raw": raw}


# ─── Internal helper: log outreach ──────────────────────────────────────────

async def _log_outreach(
    candidate_id: str | None,
    channel: str,
    direction: str,
    subject: str | None,
    body: str,
    status: str,
    metadata: dict | None = None,
    outreach_id: str | None = None,
) -> str | None:
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            if outreach_id:
                await conn.execute(
                    """
                    UPDATE outreach_log
                    SET status = $1, metadata = $2, sent_at = NOW()
                    WHERE id = $3::uuid
                    """,
                    status, json.dumps(metadata) if metadata else None, outreach_id
                )
                return outreach_id
            else:
                row = await conn.fetchrow(
                    """
                    INSERT INTO outreach_log
                      (candidate_id, channel, direction, subject, body, status, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                    """,
                    candidate_id, channel, direction, subject, body, status,
                    json.dumps(metadata) if metadata else None,
                )
                return str(row["id"]) if row else None
    except Exception as exc:
        logger.warning(f"[COMM] Failed to log outreach: {exc}")
        return None


if __name__ == "__main__":
    logger.info("Starting Communication MCP Server...")
    mcp.run(transport="stdio")
