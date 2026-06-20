"""
orchestrator.py
─────────────────────────────────────────────────────────────────────────────
Master Orchestrator — FastAPI HTTP server + background agent launcher.

Exposes REST endpoints so external systems (website webhooks, Zapier, etc.)
can inject work into the system:

  POST /ingest-resume       — Upload a candidate resume
  POST /add-job             — Manually add a VMS job requisition
  GET  /status              — Health + queue status
  GET  /candidates          — List candidates in the ATS
  GET  /requisitions        — List open VMS jobs
  GET  /submissions         — List all submissions

All agents run as asyncio tasks in the same process for simplicity.
In production, each agent can be its own Docker container / Cloud Run service.
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import asyncio
import json
import traceback
import re
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from loguru import logger
# Direct genai imports removed, parsing is now offline

from db import get_pool, close_pool
from config import get_settings
from agents.ats_agent import ATSAgent
from agents.vms_agent import VMSAgent
from agents.matching_agent import MatchingAgent
from agents.submission_agent import SubmissionAgent
from agents.self_healing_agent import SelfHealingAgent
from agents.sourcing_agent import SourcingAgent
from agents.client_outreach_agent import ClientOutreachAgent
from agents.job_posting_agent import JobPostingAgent

settings = get_settings()


# ── Lifespan: start all agents as background tasks ───────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start all agents concurrently
    logger.info("🚀 Westley Agentic System starting...")

    ats_agent      = ATSAgent()
    vms_agent      = VMSAgent()
    matching_agent = MatchingAgent()
    submission_agent = SubmissionAgent()
    healing_agent  = SelfHealingAgent()
    sourcing_agent = SourcingAgent()
    outreach_agent = ClientOutreachAgent()
    posting_agent  = JobPostingAgent()

    tasks = [
        asyncio.create_task(ats_agent.run_loop("ingest_resume"), name="ats-agent"),
        asyncio.create_task(vms_agent.run(), name="vms-agent"),
        asyncio.create_task(sourcing_agent.run(), name="sourcing-agent"),
        asyncio.create_task(matching_agent.run_loop("match_candidates"), name="matching-agent"),
        asyncio.create_task(submission_agent.run_loop("submit_candidate"), name="submission-agent-submit"),
        asyncio.create_task(submission_agent.run_loop("check_rtr_reply"), name="submission-agent-rtr"),
        asyncio.create_task(submission_agent.run_loop("ask_candidate_info"), name="submission-agent-info"),
        asyncio.create_task(healing_agent.run(), name="self-healing-agent"),
        asyncio.create_task(outreach_agent.run_loop("client_speculation"), name="client-outreach-agent"),
        asyncio.create_task(posting_agent.run(), name="job-posting-agent"),
    ]

    logger.success("✅ All agents running.")
    yield  # Server is live

    # Shutdown
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await close_pool()
    logger.info("👋 Agentic system shut down.")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Westley Resource — Agentic Placement System",
    description="Fully automated AI-driven candidate placement: ATS + VMS + MCP",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"[Orchestrator] Validation failed for {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# ── Request / Response Models ─────────────────────────────────────────────────

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

class IngestResumeRequest(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    resume_text: str

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v_clean = v.strip()
        if not EMAIL_REGEX.match(v_clean) or v_clean.endswith(".local") or "candidate.local" in v_clean:
            raise ValueError("Invalid email format. Placeholder or simulated emails (.local) are not permitted.")
        return v_clean


class AddJobRequest(BaseModel):
    title: str
    client_company: str
    description: str
    skills_required: list[str]
    location: str
    job_type: str = "Contract"
    bill_rate_max: float | None = None
    vms_platform: str = "manual"
    deadline_iso: str | None = None


class AIGenerateRequest(BaseModel):
    system: str | None = None
    userPrompt: str

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/ai/generate", tags=["AI"])
async def ai_generate(body: AIGenerateRequest):
    from gemini_client import chat_completion
    try:
        response = await chat_completion(prompt=body.userPrompt, system=body.system)
        return {"text": response}
    except Exception as e:
        logger.error(f"AI Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", tags=["Health"])
async def root():
    return {"status": "running", "system": "Westley Agentic Placement System", "version": "1.0.0"}


@app.get("/status", tags=["Health"])
async def status():
    """Get current queue stats and overall system health."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        task_stats = await conn.fetchrow(
            """
            SELECT
              COUNT(*) FILTER (WHERE status='pending')      AS pending,
              COUNT(*) FILTER (WHERE status='running')      AS running,
              COUNT(*) FILTER (WHERE status='done')         AS done,
              COUNT(*) FILTER (WHERE status='failed')       AS failed,
              COUNT(*) FILTER (WHERE status='human_review') AS human_review
            FROM agent_task_queue
            """
        )
        candidate_count = await conn.fetchval("SELECT COUNT(*) FROM candidates")
        req_count = await conn.fetchval("SELECT COUNT(*) FROM requisitions WHERE status='open'")
        submission_count = await conn.fetchval("SELECT COUNT(*) FROM submissions")

    return {
        "status": "healthy",
        "task_queue": dict(task_stats),
        "candidates_in_ats": candidate_count,
        "open_requisitions": req_count,
        "total_submissions": submission_count,
    }


@app.post("/admin/clear-human-review", tags=["Admin"])
async def clear_human_review():
    """
    Mark all existing human_review tasks as already-alerted so the
    self-healing agent stops sending repeat emails for them.
    Safe to call at any time — only affects the email flag, not task status.
    """
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
    logger.info(f"[Admin] Marked {count} human_review tasks as alerted — emails suppressed.")
    return {"cleared": count, "message": f"Marked {count} tasks as alerted. No more repeat emails."}


@app.post("/ingest-resume", tags=["ATS"])
async def ingest_resume(body: IngestResumeRequest):
    """
    Inject a candidate resume into the ATS pipeline.
    The system will automatically parse, embed, match, and reach out.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        task_id = await conn.fetchval(
            """
            INSERT INTO agent_task_queue (task_type, payload, status, max_attempts)
            VALUES ('ingest_resume', $1, 'pending', 3)
            RETURNING id
            """,
            json.dumps({
                "full_name": body.full_name,
                "email": body.email,
                "phone": body.phone,
                "resume_text": body.resume_text,
            }),
        )
    logger.info(f"[Orchestrator] Enqueued ingest_resume for {body.email} (task {task_id})")
    return {"status": "queued", "task_id": str(task_id), "candidate_email": body.email}


@app.post("/ingest-resume-file", tags=["ATS"])
async def ingest_resume_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str | None = Form(None),
    location: str | None = Form(None),
    role: str | None = Form(None),
    skills: str | None = Form(None),
    experience: str | None = Form(None),
    linkedin: str | None = Form(None),
    github: str | None = Form(None),
    message: str | None = Form(None),
):
    """
    Ingest a candidate's resume via file upload (PDF/DOCX/TXT).
    Gemini will parse the file in the cloud, extract the raw text content,
    and queue it in the self-healing ATS pipeline.
    """
    email = email.strip()
    if not EMAIL_REGEX.match(email) or email.endswith(".local") or "candidate.local" in email:
        raise HTTPException(
            status_code=422,
            detail="Invalid email format. Placeholder or simulated emails (.local) are not permitted."
        )
        
    logger.info(f"[Orchestrator] Received file upload {file.filename} for {email}")
    content = await file.read()
    
    # Check if file is empty
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        
    try:
        # Determine the file's mime type
        mime_type = file.content_type
        if not mime_type or mime_type == "application/octet-stream":
            # Guess mime type from extension
            ext = Path(file.filename).suffix.lower()
            if ext == ".pdf":
                mime_type = "application/pdf"
            elif ext == ".docx":
                mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif ext in (".doc", ".docx"):
                mime_type = "application/msword"
            else:
                mime_type = "text/plain"
        
        logger.info(f"[Orchestrator] Parsing {file.filename} ({mime_type}) offline...")
        
        # Parse text content from PDF/DOCX offline using pypdf / python-docx
        resume_text = ""
        if "text/plain" in mime_type:
            try:
                resume_text = content.decode("utf-8")
            except Exception:
                resume_text = content.decode("latin-1")
        elif "pdf" in mime_type:
            import io
            from pypdf import PdfReader
            try:
                pdf_file = io.BytesIO(content)
                reader = PdfReader(pdf_file)
                text_parts = []
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        text_parts.append(txt)
                resume_text = "\n".join(text_parts)
            except Exception as e:
                logger.error(f"Failed parsing PDF offline: {e}")
                raise ValueError(f"Failed to parse PDF resume file: {e}")
        elif any(x in mime_type for x in ("wordprocessingml", "msword", "document")):
            import io
            import zipfile
            import xml.etree.ElementTree as ET
            try:
                import docx
                docx_file = io.BytesIO(content)
                doc = docx.Document(docx_file)
                resume_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            except Exception as docx_exc:
                logger.warning(f"python-docx parse failed: {docx_exc}. Trying XML fallback...")
                try:
                    docx_file = io.BytesIO(content)
                    with zipfile.ZipFile(docx_file) as z:
                        xml_content = z.read("word/document.xml")
                    root = ET.fromstring(xml_content)
                    namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    text_elements = root.findall('.//w:t', namespaces)
                    resume_text = "".join([el.text for el in text_elements if el.text])
                except Exception as e:
                    logger.error(f"Failed parsing DOCX XML fallback: {e}")
                    raise ValueError(f"Failed to parse DOCX resume file: {e}")
        else:
            try:
                resume_text = content.decode("utf-8")
            except Exception:
                resume_text = content.decode("latin-1")
            
        if not resume_text or len(resume_text.strip()) < 50:
            raise ValueError("Parsed resume text is too short or empty. Please check the file formatting.")

        logger.success(f"[Orchestrator] Successfully parsed resume file: {len(resume_text)} characters.")
        
        # Enrich raw resume text with form-entered profile information
        rich_resume_text = f"""CANDIDATE INFORMATION (MANUALLY SUBMITTED):
Name: {name}
Email: {email}
Phone: {phone or "Not provided"}
Location: {location or "Not provided"}
Desired/Current Role: {role or "Not provided"}
Key Skills: {skills or "Not provided"}
Experience Level: {experience or "Not provided"}
LinkedIn Profile: {linkedin or "Not provided"}
GitHub/Portfolio: {github or "Not provided"}
Additional Message: {message or "Not provided"}

======================================================================
EXTRACTED RESUME TEXT CONTENT:
{resume_text}
"""
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            task_id = await conn.fetchval(
                """
                INSERT INTO agent_task_queue (task_type, payload, status, max_attempts)
                VALUES ('ingest_resume', $1, 'pending', 3)
                RETURNING id
                """,
                json.dumps({
                    "full_name": name,
                    "email": email,
                    "phone": phone,
                    "resume_text": rich_resume_text,
                }),
            )
            
        logger.info(f"[Orchestrator] Enqueued ingest_resume for {email} (task {task_id}) via file upload")
        return {"status": "queued", "task_id": str(task_id), "candidate_email": email}
        
    except Exception as e:
        logger.error(f"[Orchestrator] File parsing/ingestion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse or ingest resume file. Error: {str(e)}"
        )


@app.post("/add-job", tags=["VMS"])
async def add_job(body: AddJobRequest):
    """
    Manually add a VMS job requisition. The system will automatically
    find and reach out to matching candidates.
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from agents.base_agent import VMS_SERVER
    import json as j

    import os as _os
    async with stdio_client(StdioServerParameters(command="python", args=[VMS_SERVER], env=dict(_os.environ))) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool("add_requisition", arguments={
                "title": body.title,
                "client_company": body.client_company,
                "description": body.description,
                "skills_required": body.skills_required,
                "location": body.location,
                "job_type": body.job_type,
                "bill_rate_max": body.bill_rate_max,
                "vms_platform": body.vms_platform,
                "deadline_iso": body.deadline_iso,
            })
            raw = result.content[0].text if result.content else "{}"
            req = j.loads(raw)

    # Queue matching and job posting
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO agent_task_queue (task_type, payload) VALUES ('match_candidates', $1)",
            json.dumps({"requisition_id": req["id"], "trigger": "manual_add"}),
        )
        await conn.execute(
            "INSERT INTO agent_task_queue (task_type, payload) VALUES ('post_to_job_boards', $1)",
            json.dumps({"requisition_id": req["id"], "title": req["title"], "location": req.get("location", "")}),
        )

    return {"status": "queued", "requisition_id": req["id"], "title": req["title"]}


@app.get("/candidates", tags=["ATS"])
async def list_candidates(status: str = "active", limit: int = 50):
    """List candidates in the ATS."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, full_name, email, phone, skills, experience_years,
                   current_title, location, status, rtr_given, created_at
            FROM candidates WHERE status = $1 ORDER BY created_at DESC LIMIT $2
            """,
            status, limit,
        )
    return [dict(r) | {"id": str(r["id"]), "created_at": r["created_at"].isoformat()} for r in rows]


@app.get("/requisitions", tags=["VMS"])
async def list_requisitions(status: str = "open", limit: int = 50):
    """List VMS requisitions."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, vms_platform, title, client_company, skills_required,
                   location, job_type, bill_rate_max, status, created_at,
                   client_contact_name, client_contact_email, client_contact_phone
            FROM requisitions WHERE status = $1 ORDER BY created_at DESC LIMIT $2
            """,
            status, limit,
        )
    return [dict(r) | {"id": str(r["id"]), "created_at": r["created_at"].isoformat()} for r in rows]
@app.get("/requisitions/{req_id}", tags=["VMS"])
async def list_requisition_by_id(req_id: str):
    """Get a specific requisition by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM requisitions WHERE id = $1::uuid", req_id)
        if not row:
            raise HTTPException(status_code=404, detail="Requisition not found")
        
        import json
        from fastapi.responses import Response
        
        job_dict = dict(row)
        
        # Serialize UUIDs and Datetimes to strings safely
        def _default(obj):
            import datetime
            import uuid
            import decimal
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()
            if isinstance(obj, uuid.UUID):
                return str(obj)
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            return str(obj)
            
        if isinstance(job_dict.get('skills_required'), str):
            try:
                job_dict['skills_required'] = json.loads(job_dict['skills_required'])
            except:
                pass
                
        return Response(content=json.dumps(job_dict, default=_default), media_type="application/json")

@app.post("/requisitions/{req_id}/match", tags=["VMS"])
async def trigger_requisition_match(req_id: str):
    """Manually trigger candidate matching & auto-apply for a specific requisition."""
    pool = await get_pool()
    import json
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM requisitions WHERE id = $1::uuid", req_id)
        if not row:
            raise HTTPException(status_code=404, detail="Requisition not found")
        
        await conn.execute(
            "INSERT INTO agent_task_queue (task_type, payload) VALUES ('match_candidates', $1)",
            json.dumps({"requisition_id": str(row["id"]), "trigger": "manual_match_ui"}),
        )
    return {"status": "success", "message": "Matching and auto-apply queued."}

@app.post("/candidates/{candidate_id}/match", tags=["ATS"])
async def trigger_candidate_match(candidate_id: str):
    """Manually trigger finding matching jobs for a specific candidate."""
    pool = await get_pool()
    import json
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM candidates WHERE id = $1::uuid", candidate_id)
        if not row:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        await conn.execute(
            "INSERT INTO agent_task_queue (task_type, payload) VALUES ('match_candidates', $1)",
            json.dumps({"candidate_id": str(row["id"]), "trigger": "manual_candidate_match_ui"}),
        )
    return {"status": "success", "message": "Job matching process queued for candidate."}

@app.get("/submissions", tags=["Submissions"])
async def list_submissions(limit: int = 50):
    """List all candidate submissions."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.id, s.vms_submission_id, s.status, s.bill_rate_submitted,
                   s.submitted_at, c.full_name AS candidate, c.email,
                   r.title AS job_title, r.vms_platform
            FROM submissions s
            JOIN candidates c ON c.id = s.candidate_id
            JOIN requisitions r ON r.id = s.requisition_id
            ORDER BY s.submitted_at DESC LIMIT $1
            """,
            limit,
        )
    return [dict(r) | {"id": str(r["id"]), "submitted_at": r["submitted_at"].isoformat()} for r in rows]


@app.get("/health-log", tags=["Health"])
async def health_log(limit: int = 100):
    """Recent agent health events."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM agent_health_log ORDER BY logged_at DESC LIMIT $1", limit
        )
    return [dict(r) | {"id": str(r["id"]), "logged_at": r["logged_at"].isoformat()} for r in rows]


# ── Outreach human review endpoints ──────────────────────────────────────────

class EditOutreachRequest(BaseModel):
    to_address: str
    subject: str
    body: str

@app.get("/api/outreach/pending", tags=["Outreach"])
async def list_pending_outreach():
    """List all outreach communications pending review."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, candidate_id, channel, direction, subject, body, status, metadata, sent_at
            FROM outreach_log
            WHERE status = 'pending_review'
            ORDER BY sent_at DESC
            """
        )
    return [
        {
            "id": str(r["id"]),
            "candidate_id": str(r["candidate_id"]) if r["candidate_id"] else None,
            "channel": r["channel"],
            "direction": r["direction"],
            "subject": r["subject"],
            "body": r["body"],
            "status": r["status"],
            "metadata": r["metadata"],
            "sent_at": r["sent_at"].isoformat()
        } for r in rows
    ]

@app.post("/api/outreach/pending/{outreach_id}/approve", tags=["Outreach"])
async def approve_outreach(outreach_id: str):
    """Approve a pending outreach email and send it."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, subject, body, metadata, candidate_id FROM outreach_log WHERE id = $1::uuid AND status = 'pending_review'",
            outreach_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Pending outreach not found or already processed.")
            
        metadata = row["metadata"] or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        to_address = metadata.get("to_address")
        if not to_address:
            raise HTTPException(status_code=400, detail="Recipient address (to_address) not found in metadata.")
            
        import os
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from agents.base_agent import COMM_SERVER
        
        try:
            async with stdio_client(StdioServerParameters(command=sys.executable, args=[COMM_SERVER], env=dict(os.environ))) as (rc, wc):
                async with ClientSession(rc, wc) as comm:
                    await comm.initialize()
                    result = await comm.call_tool(
                        "send_email",
                        arguments={
                            "to_address": to_address,
                            "subject": row["subject"],
                            "body_html": row["body"],
                            "candidate_id": str(row["candidate_id"]) if row["candidate_id"] else None,
                            "bypass_review": True,
                            "outreach_id": outreach_id
                        }
                    )
                    
                    if result.isError:
                        error_text = result.content[0].text if result.content else "Unknown error"
                        raise RuntimeError(error_text)
                        
                    parsed = json.loads(result.content[0].text) if result.content else {}
                    if parsed.get("status") == "failed":
                        raise RuntimeError(parsed.get("error", "Email sending failed"))
                        
                    return {"status": parsed.get("status") or "sent", "message": "Email approved and sent."}
                    
        except Exception as e:
            logger.error(f"Failed to send approved email: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.post("/api/outreach/pending/{outreach_id}/edit", tags=["Outreach"])
async def edit_and_approve_outreach(outreach_id: str, request_body: EditOutreachRequest):
    """Edit a pending outreach email, then approve and send it."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, metadata, candidate_id FROM outreach_log WHERE id = $1::uuid AND status = 'pending_review'",
            outreach_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Pending outreach not found or already processed.")
            
        metadata = row["metadata"] or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        metadata["to_address"] = request_body.to_address
        
        await conn.execute(
            """
            UPDATE outreach_log
            SET subject = $1, body = $2, metadata = $3
            WHERE id = $4::uuid
            """,
            request_body.subject, request_body.body, json.dumps(metadata), outreach_id
        )
        
        import os
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from agents.base_agent import COMM_SERVER
        
        try:
            async with stdio_client(StdioServerParameters(command=sys.executable, args=[COMM_SERVER], env=dict(os.environ))) as (rc, wc):
                async with ClientSession(rc, wc) as comm:
                    await comm.initialize()
                    result = await comm.call_tool(
                        "send_email",
                        arguments={
                            "to_address": request_body.to_address,
                            "subject": request_body.subject,
                            "body_html": request_body.body,
                            "candidate_id": str(row["candidate_id"]) if row["candidate_id"] else None,
                            "bypass_review": True,
                            "outreach_id": outreach_id
                        }
                    )
                    
                    if result.isError:
                        error_text = result.content[0].text if result.content else "Unknown error"
                        raise RuntimeError(error_text)
                        
                    parsed = json.loads(result.content[0].text) if result.content else {}
                    if parsed.get("status") == "failed":
                        raise RuntimeError(parsed.get("error", "Email sending failed"))
                        
                    return {"status": parsed.get("status") or "sent", "message": "Email updated and sent."}
                    
        except Exception as e:
            logger.error(f"Failed to send edited email: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.post("/api/outreach/pending/{outreach_id}/reject", tags=["Outreach"])
async def reject_outreach(outreach_id: str):
    """Reject a pending outreach email."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE outreach_log SET status = 'rejected' WHERE id = $1::uuid AND status = 'pending_review'",
            outreach_id
        )
        count = int(result.split(" ")[-1])
        if count == 0:
            raise HTTPException(status_code=404, detail="Pending outreach not found or already processed.")
        return {"status": "rejected", "message": "Email rejected and discarded."}


# ── Entry point ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "orchestrator:app",
        host="0.0.0.0",
        port=settings.ORCHESTRATOR_PORT,
        reload=False,
        log_level="info",
    )
