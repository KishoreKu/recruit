# Westley Resource: Automated Job Scheduling Architecture Guide

This document outlines how the automated recruitment background jobs and agent fleet are scheduled, queued, and executed. It also describes the interactive React scheduler board we added to the frontend dashboard.

---

## 1. Architectural Block Diagram

The diagram below visualizes the flow of scheduling triggers, the API gateway, the transactional database queue, and the background agent execution loop.

```mermaid
graph TD
    %% Define Nodes
    subgraph Triggers ["1. Trigger Sources"]
        VMS_Cron["VMS Sync Cron Trigger<br/>(Every 1 Hour)"]
        Resume_Event["Candidate Resume Upload<br/>(Instant HTTP POST)"]
        Self_Healing_Cron["Self-Healing Cron<br/>(Every 5 Minutes)"]
    end

    subgraph API_Gateway ["2. Gateway (FastAPI)"]
        Orchestrator["FastAPI Orchestrator<br/>(Azure Container App)"]
    end

    subgraph Queue_Broker ["3. Queue Broker"]
        Postgres_DB[("PostgreSQL Queue Table<br/>(State: pending, running, completed)")]
    end

    subgraph Worker_Fleet ["4. Background Agent Fleet"]
        VMS_Sync_Agent["VMS Sync Worker<br/>(Polls 1hr, Syncs Requisitions)"]
        Matching_Agent["AI Matching Worker<br/>(Polls 2s, Cosine Vector Search)"]
        Self_Healing_Agent["Self-Healing Worker<br/>(Polls 5m, Requeues Stuck Jobs)"]
    end

    subgraph Integrations ["5. External Connections"]
        MS_Graph["Microsoft Graph API<br/>(SMTP Client Email Alerts)"]
        VMS_Portals["Fieldglass / Beeline Portal<br/>(Requisition Scraping)"]
    end

    %% Flows
    VMS_Cron -->|Schedule Event| Orchestrator
    Resume_Event -->|Multipart File Stream| Orchestrator
    Self_Healing_Cron -->|Schedule Event| Orchestrator

    Orchestrator -->|1. LLM OCR Parsing via Gemini 2.0| Postgres_DB
    Orchestrator -->|2. Insert Task to Queue| Postgres_DB

    VMS_Sync_Agent <-->|Polls Queue / Upserts Requisitions| Postgres_DB
    Matching_Agent <-->|Polls Task Queue / Calculates Matches| Postgres_DB
    Self_Healing_Agent <-->|Polls Tasks / Detects Overdue (>15m)| Postgres_DB

    VMS_Sync_Agent -->|Scrape Job Orders| VMS_Portals
    Self_Healing_Agent -->|SMTP Warning Mails| MS_Graph
    Matching_Agent -->|Email Match Alerts / RTR Requests| MS_Graph
```

---

## 2. Automated Agent Details & Intervals

| Component / Agent | Trigger / Schedule Interval | Queue Task Type | DB State Changes | Primary Function |
| :--- | :--- | :--- | :--- | :--- |
| **VMS Sync Trigger** | Hourly Cron Pattern | `sync_vms` | Inserts `pending` tasks | Initiates background scraper cycles. |
| **Candidate Form** | Instant User Submission | `match_candidate` | Inserts `pending` tasks | Triggers instant OCR parsing and matching. |
| **FastAPI Orchestrator** | Event-driven API Gateway | N/A | Writes to `tasks` & `requisitions` | Authenticates queries, processes Gemini OCR, writes vector embeddings. |
| **VMS Sync Worker** | Polled (claim tasks every 1 hr) | `sync_vms` | Claims `pending` $\rightarrow$ `running` $\rightarrow$ `completed` | Scrapes portal jobs, adds them to `requisitions`. |
| **AI Matching Worker** | Continuous polling (every 2 seconds) | `match_candidate` | Claims `pending` $\rightarrow$ `running` $\rightarrow$ `completed` | Calculates candidate-to-job matches using vector distance. |
| **Self-Healing Agent** | Polled (every 5 minutes) | `monitor_health` | Resets `running` $\rightarrow$ `pending` or `failed` | Inspects stuck jobs, logs errors, alerts admins via email. |
| **Microsoft Graph API** | Event-driven Webhooks / OAuth 2.0 | N/A | N/A | Handles automated recruiter/candidate email communication. |

---

## 3. Database Queue Implementation (SELECT FOR UPDATE SKIP LOCKED)

To avoid concurrency bugs where multiple instances of the same background agent pick up the same job, the Postgres task queue is built using transaction-safe row locking:

```sql
-- Fetch and claim the next available task atomically
UPDATE tasks
SET 
  status = 'running', 
  claimed_by = 'matching_agent_instance_1', 
  started_at = NOW()
WHERE id = (
  SELECT id FROM tasks 
  WHERE status = 'pending' 
  ORDER BY created_at ASC
  FOR UPDATE SKIP LOCKED 
  LIMIT 1
) 
RETURNING *;
```

> [!NOTE]
> `FOR UPDATE SKIP LOCKED` guarantees that if another container is currently evaluating the same task row, the database skips it and hands the next task to the requesting worker, preventing duplication.

---

## 4. The Interactive React HTML Dashboard

To visualize this flow, we created a dashboard page under `/scheduler` in the React frontend:

- **Path**: `/scheduler`
- **Location**: [SchedulerPage.jsx](file:///Users/kishorekumar/CascadeProjects/westleyresource/client/src/pages/SchedulerPage.jsx)
- **Features**:
  1. **Dynamic SVG Connections**: Connects the blocks using SVG paths with animated glowing dash arrays that flow between columns representing active data channels.
  2. **Interactive Block Inspection**: Clicking a block displays its description, system parameters, and code snippets (e.g. FastAPI route handlers, Python daemon loops, database transaction scripts).
  3. **Event Workflow Simulator**: Includes automated playbooks for **Resume Ingestion** and **Hourly VMS Syncs** that simulate task creation, worker loops, logs, and database status updates.
  4. **Cron Playground**: Computes upcoming runtimes for customizable patterns (e.g. `*/5 * * * *`) to demonstrate how timers evaluate schedules.
