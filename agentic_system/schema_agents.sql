-- ============================================================
--  Agentic AI Candidate Placement System — Database Schema
--  Extends the existing jobs/users/saved_jobs schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector for semantic search

-- ─────────────────────────────────────────────────────────────
-- CANDIDATES: Parsed resume data + 768-dim Gemini embedding
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  full_name        VARCHAR(255) NOT NULL,
  email            VARCHAR(255) UNIQUE NOT NULL,
  phone            VARCHAR(50),
  skills           TEXT[],
  experience_years INTEGER,
  current_title    VARCHAR(255),
  current_company  VARCHAR(255),
  location         VARCHAR(255),
  visa_status      VARCHAR(100),         -- H1B, GC, Citizen, etc.
  bill_rate        NUMERIC(10, 2),        -- expected hourly rate
  resume_raw       TEXT,                  -- raw resume text
  resume_file_url  TEXT,                  -- cloud storage URL
  embedding        vector(768),           -- text-embedding-004
  status           VARCHAR(50) DEFAULT 'active',  -- active | placed | inactive
  rtr_given        BOOLEAN DEFAULT FALSE,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);
-- NOTE: We comment out this approximate index because for smaller datasets (<10,000 rows),
-- pgvector exact sequential scanning is fast and guarantees 100% recall.
-- Having an IVFFlat index with lists=100 on a small database restricts search results.
-- CREATE INDEX IF NOT EXISTS candidates_embedding_idx
--   ON candidates USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);


-- ─────────────────────────────────────────────────────────────
-- REQUISITIONS: VMS job requisitions
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS requisitions (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  vms_platform     VARCHAR(100) NOT NULL,   -- Fieldglass, Beeline, Workday, etc.
  vms_job_id       VARCHAR(255),
  title            VARCHAR(255) NOT NULL,
  client_company   VARCHAR(255),
  skills_required  TEXT[],
  location         VARCHAR(255),
  job_type         VARCHAR(100),
  bill_rate_max    NUMERIC(10, 2),
  description      TEXT,
  embedding        vector(768),
  status           VARCHAR(50) DEFAULT 'open',  -- open | filled | expired | cancelled
  deadline         TIMESTAMPTZ,
  client_contact_name VARCHAR(255),
  client_contact_email VARCHAR(255),
  client_contact_phone VARCHAR(50),
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- SUBMISSIONS: Candidate → Requisition submissions
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS submissions (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  candidate_id      UUID REFERENCES candidates(id) ON DELETE CASCADE,
  requisition_id    UUID REFERENCES requisitions(id) ON DELETE CASCADE,
  vms_submission_id VARCHAR(255),             -- confirmation ID from VMS
  bill_rate_submitted NUMERIC(10, 2),
  status            VARCHAR(50) DEFAULT 'submitted',
  -- submitted | client_review | interview | offered | placed | rejected
  notes             TEXT,
  submitted_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(candidate_id, requisition_id)
);

-- ─────────────────────────────────────────────────────────────
-- OUTREACH_LOG: Every automated communication the agents send
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS outreach_log (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  candidate_id    UUID REFERENCES candidates(id),
  channel         VARCHAR(50) NOT NULL,  -- email | sms | whatsapp
  direction       VARCHAR(10) NOT NULL,  -- outbound | inbound
  subject         TEXT,
  body            TEXT NOT NULL,
  status          VARCHAR(50) DEFAULT 'sent',  -- sent | delivered | bounced | replied
  metadata        JSONB,
  sent_at         TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- AGENT_TASK_QUEUE: Orchestrator task queue with retry/circuit-breaker state
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_task_queue (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  task_type       VARCHAR(100) NOT NULL,
  -- ingest_resume | match_candidates | send_outreach | submit_candidate
  -- check_submission_status | refresh_token | retry_failed
  payload         JSONB NOT NULL,
  status          VARCHAR(50) DEFAULT 'pending',
  -- pending | running | done | failed | human_review
  attempts        INTEGER DEFAULT 0,
  max_attempts    INTEGER DEFAULT 3,       -- circuit breaker threshold
  last_error      TEXT,
  assigned_agent  VARCHAR(100),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),
  scheduled_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS task_queue_status_idx
  ON agent_task_queue (status, scheduled_at);

-- ─────────────────────────────────────────────────────────────
-- AGENT_HEALTH_LOG: Self-healing monitor audit trail
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_health_log (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_name  VARCHAR(100) NOT NULL,
  event_type  VARCHAR(100) NOT NULL,  -- started | succeeded | failed | recovered | circuit_open
  message     TEXT,
  metadata    JSONB,
  logged_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Helper: auto-update updated_at timestamps
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DO $$ DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['candidates','requisitions','submissions','agent_task_queue']
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_upd_%I ON %I;
      CREATE TRIGGER trg_upd_%I BEFORE UPDATE ON %I
      FOR EACH ROW EXECUTE PROCEDURE update_updated_at();', t, t, t, t);
  END LOOP;
END $$;

-- ─────────────────────────────────────────────────────────────
-- ALTER TABLE updates to support client contact lead enrichment
-- ─────────────────────────────────────────────────────────────
ALTER TABLE requisitions ADD COLUMN IF NOT EXISTS client_contact_name VARCHAR(255);
ALTER TABLE requisitions ADD COLUMN IF NOT EXISTS client_contact_email VARCHAR(255);
ALTER TABLE requisitions ADD COLUMN IF NOT EXISTS client_contact_phone VARCHAR(50);
