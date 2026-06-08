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
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from loguru import logger
# Direct genai imports removed, parsing is now offline

from db import get_pool, close_pool
from config import get_settings
from agents.ats_agent import ATSAgent
from agents.vms_agent import VMSAgent
from agents.matching_agent import MatchingAgent
from agents.submission_agent import SubmissionAgent
from agents.self_healing_agent import SelfHealingAgent

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

    tasks = [
        asyncio.create_task(ats_agent.run_loop("ingest_resume"), name="ats-agent"),
        asyncio.create_task(vms_agent.run(), name="vms-agent"),
        asyncio.create_task(matching_agent.run_loop("match_candidates"), name="matching-agent"),
        asyncio.create_task(submission_agent.run_loop("submit_candidate"), name="submission-agent-submit"),
        asyncio.create_task(submission_agent.run_loop("check_rtr_reply"), name="submission-agent-rtr"),
        asyncio.create_task(submission_agent.run_loop("ask_candidate_info"), name="submission-agent-info"),
        asyncio.create_task(healing_agent.run(), name="self-healing-agent"),
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

class IngestResumeRequest(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    resume_text: str


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

    # Queue matching
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO agent_task_queue (task_type, payload) VALUES ('match_candidates', $1)",
            json.dumps({"requisition_id": req["id"], "trigger": "manual_add"}),
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
                   location, job_type, bill_rate_max, status, created_at
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
        
        # Convert skills arrays/JSON properly if needed
        job_dict = dict(row)
        if isinstance(job_dict.get('skills_required'), str):
            try:
                job_dict['skills_required'] = json.loads(job_dict['skills_required'])
            except:
                pass
                
        return job_dict

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
