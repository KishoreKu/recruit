import React, { useState, useEffect } from 'react';
import {
  Clock, Server, Database, Cpu, Mail, ArrowRight, Play,
  RefreshCw, CheckCircle, AlertCircle, Code, Workflow, Eye,
  Sparkles, Layers, ListTodo, Send, Check
} from 'lucide-react';

// Definitions for the architectural blocks
const BLOCKS = {
  vms_cron: {
    id: 'vms_cron',
    title: 'VMS Sync Trigger',
    type: 'trigger',
    status: 'Sleeping',
    interval: 'Every 1 Hour',
    icon: Clock,
    color: 'var(--warn)',
    description: 'A scheduled background timer triggers the VMS sync job to look for new requisitions.',
    details: 'Runs on Azure Container Apps as an automated cron loop. It fires every hour, initiating a VMS portal scrape.',
    code: `// python/vms_trigger.py (Azure Cron Worker)
import asyncio

async def main():
    print("VMS Cron Trigger fired! Enqueuing sync job...")
    await db.enqueue_task(
        task_type="sync_vms",
        payload={"platforms": ["Fieldglass", "Beeline"]}
    )

if __name__ == "__main__":
    asyncio.run(main())`
  },
  resume_upload: {
    id: 'resume_upload',
    title: 'Resume Ingest Trigger',
    type: 'trigger',
    status: 'Idle',
    interval: 'Instant (Event)',
    icon: UploadIcon,
    color: 'var(--primary)',
    description: 'Triggered instantly when a candidate submits their details or uploads a resume PDF.',
    details: 'The web browser issues a multipart/form-data POST request to the API, sending the raw file stream for immediate processing.',
    code: `// client/src/pages/CandidatesPage.jsx (React)
const handleUpload = async (file) => {
  const formData = new FormData();
  formData.append("resume", file);
  
  // Triggers instant background processing
  const res = await axios.post("/api/ingest-resume-file", formData);
  showNotification("Resume uploaded! Job enqueued: " + res.data.task_id);
};`
  },
  orchestrator: {
    id: 'orchestrator',
    title: 'FastAPI Orchestrator',
    type: 'gateway',
    status: 'Online',
    interval: 'Active API Gateway',
    icon: Server,
    color: 'var(--primary-glow)',
    description: 'The gateway API. Extracts text using Gemini 2.0 Flash and inserts tasks into the Postgres queue.',
    details: 'Runs on Azure Container Apps. When a resume is received, it extracts text, generates metadata, and adds a matching task to the DB queue.',
    code: `# server/orchestrator.py (FastAPI)
@app.post("/ingest-resume-file")
async def ingest_resume(file: UploadFile, background_tasks: BackgroundTasks):
    # 1. Parse text using Gemini 2.0 Flash
    text = await gemini_client.extract_resume_text(file)
    
    # 2. Enqueue in Database Task Queue
    task_id = await db.enqueue_task(
        task_type="match_candidate",
        payload={"text": text, "filename": file.filename}
    )
    return {"status": "queued", "task_id": task_id}`
  },
  postgres_queue: {
    id: 'postgres_queue',
    title: 'PostgreSQL Task Queue',
    type: 'database',
    status: 'Active',
    interval: 'State Store & Queue',
    icon: Database,
    color: 'var(--accent)',
    description: 'The core state database. Holds the queue of pending, running, completed, and failed tasks.',
    details: 'Uses Postgres transactional locking (SELECT FOR UPDATE SKIP LOCKED) to allow multiple agents to fetch tasks without concurrency conflicts.',
    code: `-- sql/fetch_next_task.sql
UPDATE tasks
SET 
  status = 'running', 
  claimed_by = :agent_name, 
  started_at = NOW()
WHERE id = (
  SELECT id FROM tasks 
  WHERE status = 'pending' 
  ORDER BY created_at ASC
  FOR UPDATE SKIP LOCKED 
  LIMIT 1
) RETURNING *;`
  },
  vms_agent: {
    id: 'vms_agent',
    title: 'VMS Agent Worker',
    type: 'agent',
    status: 'Sleeping',
    interval: 'Polled (1 hr)',
    icon: Cpu,
    color: 'var(--purple)',
    description: 'Syncs job postings from VMS portals (Fieldglass, Beeline) into the local requisitions database.',
    details: 'Pulls job orders periodically, maps job metadata, extracts required skills, and writes them as new open Requisitions.',
    code: `# agents/vms_agent.py
async def process_sync_task(task_payload):
    # Log in to VMS portals and fetch postings
    raw_jobs = await scrape_vms_platforms()
    for job in raw_jobs:
        parsed_job = await parse_job_with_gemini(job)
        # Store in db. Requisition entry automatically triggers matcher
        await db.create_requisition(parsed_job)`
  },
  matching_agent: {
    id: 'matching_agent',
    title: 'AI Matching Agent',
    type: 'agent',
    status: 'Active',
    interval: 'Continuous Polling',
    icon: Cpu,
    color: 'var(--purple)',
    description: 'Compares candidates and job requisitions using Postgres vector embeddings & Gemini scoring.',
    details: 'Queries PGVector for candidates matching job skills, computes similarity, filters by RTR validity, and flags matches.',
    code: `# agents/matching_agent.py
async def run_matching_loop():
    while True:
        task = await db.claim_task("match_candidate")
        if task:
            cand_id = task.payload["candidate_id"]
            # Perform vector search
            matches = await db.query_pgvector_matches(cand_id, threshold=0.75)
            # Log results and save
            await db.save_matches(cand_id, matches)
            await db.complete_task(task.id)
        await asyncio.sleep(2) # Polling throttle`
  },
  self_healing_agent: {
    id: 'self_healing_agent',
    title: 'Self-Healing Monitor',
    type: 'agent',
    status: 'Active',
    interval: 'Every 5 Mins',
    icon: Cpu,
    color: 'var(--danger)',
    description: 'Requeues tasks stuck in "running" status for too long and fires email alerts via Microsoft Graph API.',
    details: 'Runs every 5 minutes. If a task is marked "running" for over 15 minutes, it is assumed crashed, marked as failed/requeued, and recruiters are notified.',
    code: `# agents/self_healing_agent.py
async def monitor_queue_health():
    # Find stuck tasks
    stuck_tasks = await db.get_stuck_tasks(timeout_seconds=900)
    for task in stuck_tasks:
        print(f"Stuck task detected: {task.id}. Auto-requeuing...")
        await db.requeue_task(task.id)
        await email_service.send_alert(
            recipient="support@westleyresource.com",
            subject=f"⚠️ Automated Repair Alert: Task {task.id}",
            body=f"Task of type {task.type} was stuck and has been auto-requeued."
        )`
  },
  ms_graph: {
    id: 'ms_graph',
    title: 'Microsoft Graph SMTP',
    type: 'external',
    status: 'Connected',
    interval: 'On-Demand Integration',
    icon: Mail,
    color: 'var(--accent)',
    description: 'Sends emails for RTR verification request, match notifications, and critical system failure alerts.',
    details: 'Uses Microsoft Entra ID OAuth 2.0 app credentials to authenticate securely, sending mails via the authorized sender account.',
    code: `// functions/src/email.js (Cloud Function)
const getAccessToken = async () => {
  const params = new URLSearchParams({
    client_id: process.env.MS_CLIENT_ID,
    client_secret: process.env.MS_CLIENT_SECRET,
    scope: "https://graph.microsoft.com/.default",
    grant_type: "client_credentials"
  });
  const res = await axios.post(
    \`https://login.microsoftonline.com/\${process.env.MS_TENANT_ID}/oauth2/v2.0/token\`,
    params
  );
  return res.data.access_token;
};`
  }
};

// SVG Icon wrapper for upload since Upload isn't imported from lucide-react in top list
function UploadIcon(props) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

export default function SchedulerPage() {
  const [activeTab, setActiveTab] = useState('diagram');
  const [selectedBlock, setSelectedBlock] = useState('orchestrator');
  
  // States for Queue Simulator
  const [simulatorTasks, setSimulatorTasks] = useState([
    { id: 't-1', name: 'Resume Ingestion: Jane_Doe.pdf', type: 'ingest', status: 'completed', time: '5m ago', color: 'var(--primary)' },
    { id: 't-2', name: 'Matching: Jane Doe ↔ Cloud Eng', type: 'match', status: 'completed', time: '4m ago', color: 'var(--purple)' },
    { id: 't-3', name: 'VMS Sync: Fieldglass Check', type: 'sync', status: 'running', time: 'Just now', color: 'var(--warn)' },
    { id: 't-4', name: 'Send RTR Email: Jane Doe', type: 'email', status: 'pending', time: 'Queued', color: 'var(--accent)' }
  ]);
  const [simLogs, setSimLogs] = useState([
    { time: '15:40:02', sender: 'system', text: '📅 System startup. Scheduler daemon listening...' },
    { time: '15:41:12', sender: 'orchestrator', text: '📥 Received POST /ingest-resume-file for Jane_Doe.pdf. Text extracted via Gemini 2.0.' },
    { time: '15:41:14', sender: 'postgres_queue', text: '💾 Enqueued task ingest_resume (ID: t-1) & matching (ID: t-2).' },
    { time: '15:42:01', sender: 'matching_agent', text: '🤖 Matching Agent claimed task t-2. Calculating cosine similarity via PGVector...' },
    { time: '15:42:05', sender: 'matching_agent', text: '✅ Candidate Jane Doe matches Senior Cloud Engineer with 89% score. RTR task enqueued (ID: t-4).' }
  ]);
  const [simulating, setSimulating] = useState(false);
  const [activeFlow, setActiveFlow] = useState(null); // 'resume' or 'cron'

  // States for Cron Playground
  const [cronInput, setCronInput] = useState('*/5 * * * *');
  const [cronSummary, setCronSummary] = useState('Every 5 minutes');
  const [simulatedTimes, setSimulatedTimes] = useState([]);
  
  // Calculate simulated cron run times
  useEffect(() => {
    calculateCronTimes(cronInput);
  }, [cronInput]);

  const calculateCronTimes = (pattern) => {
    const times = [];
    const now = new Date();
    
    // Simple cron description & run times generator
    if (pattern.trim() === '*/5 * * * *') {
      setCronSummary('Every 5 minutes');
      for (let i = 1; i <= 5; i++) {
        const d = new Date(now.getTime() + i * 5 * 60 * 1000);
        d.setSeconds(0);
        times.push(d.toLocaleTimeString());
      }
    } else if (pattern.trim() === '0 * * * *') {
      setCronSummary('Every hour at minute 0');
      for (let i = 1; i <= 5; i++) {
        const d = new Date(now.getTime());
        d.setHours(d.getHours() + i);
        d.setMinutes(0);
        d.setSeconds(0);
        times.push(d.toLocaleTimeString());
      }
    } else if (pattern.trim() === '*/15 * * * *') {
      setCronSummary('Every 15 minutes');
      for (let i = 1; i <= 5; i++) {
        const d = new Date(now.getTime() + i * 15 * 60 * 1000);
        d.setSeconds(0);
        times.push(d.toLocaleTimeString());
      }
    } else if (pattern.trim() === '0 0 * * *') {
      setCronSummary('Every day at midnight (12:00 AM)');
      for (let i = 1; i <= 5; i++) {
        const d = new Date(now.getTime());
        d.setDate(d.getDate() + i);
        d.setHours(0); d.setMinutes(0); d.setSeconds(0);
        times.push(d.toLocaleDateString() + ' 12:00:00 AM');
      }
    } else {
      setCronSummary('Custom Schedule Pattern');
      // Mock some times
      for (let i = 1; i <= 5; i++) {
        const d = new Date(now.getTime() + i * 10 * 60 * 1000);
        times.push(d.toLocaleTimeString());
      }
    }
    setSimulatedTimes(times);
  };

  // Run a full simulation sequence
  const startResumeSimulation = () => {
    if (simulating) return;
    setSimulating(true);
    setActiveFlow('resume');
    
    // Clear previous simulated queue & logs for this run
    setSimulatorTasks([
      { id: 't-new-1', name: 'Resume Ingestion: Candidate_Resume.pdf', type: 'ingest', status: 'pending', time: 'Queued', color: 'var(--primary)' }
    ]);
    
    const logs = [];
    const addLog = (sender, text) => {
      const nowStr = new Date().toLocaleTimeString();
      logs.push({ time: nowStr, sender, text });
      setSimLogs([...logs]);
    };
    
    addLog('system', '⚡ Simulated Resume Ingestion trigger fired.');
    
    setTimeout(() => {
      // Step 1: Upload to Orchestrator
      addLog('orchestrator', '📥 Parsing PDF text stream using Gemini 2.0 Flash API...');
      setSimulatorTasks(prev => [
        { ...prev[0], status: 'running', time: 'Running' }
      ]);
      
      setTimeout(() => {
        // Step 2: Enqueue in Postgres
        addLog('postgres_queue', '💾 PDF parsed successfully. Generated candidate embeddings (vector size: 768). Enqueued: "Match Requisitions" (Task t-new-2).');
        setSimulatorTasks(prev => [
          { ...prev[0], status: 'completed', time: 'Completed' },
          { id: 't-new-2', name: 'Matching: Resume ↔ Requisitions', type: 'match', status: 'pending', time: 'Queued', color: 'var(--purple)' }
        ]);
        
        setTimeout(() => {
          // Step 3: Matcher claims
          addLog('matching_agent', '🤖 Matching Agent polled & claimed task t-new-2. Running Cosine Distance query in DB...');
          setSimulatorTasks(prev => [
            prev[0],
            { ...prev[1], status: 'running', time: 'Running' }
          ]);
          
          setTimeout(() => {
            // Step 4: Found match, enqueues RTR Email
            addLog('matching_agent', '🎯 High match found (82% similarity) with "Senior Cloud Engineer" (Req #912). Enqueuing RTR validation email task...');
            setSimulatorTasks(prev => [
              prev[0],
              { ...prev[1], status: 'completed', time: 'Completed' },
              { id: 't-new-3', name: 'Send RTR Email: Candidate', type: 'email', status: 'pending', time: 'Queued', color: 'var(--accent)' }
            ]);
            
            setTimeout(() => {
              // Step 5: Send Mail via MS Graph API
              addLog('ms_graph', '📧 Dispatching Right-to-Represent (RTR) email to candidate using MS Graph API.');
              setSimulatorTasks(prev => [
                prev[0],
                prev[1],
                { ...prev[2], status: 'running', time: 'Sending...' }
              ]);
              
              setTimeout(() => {
                addLog('ms_graph', '✅ RTR validation email sent successfully. Recruiter notified.');
                setSimulatorTasks(prev => [
                  prev[0],
                  prev[1],
                  { ...prev[2], status: 'completed', time: 'Sent' }
                ]);
                addLog('system', '🏁 Simulation complete. All processes resolved successfully.');
                setSimulating(false);
                setActiveFlow(null);
              }, 1500);
              
            }, 1500);
            
          }, 1800);
          
        }, 1500);
        
      }, 1500);
      
    }, 1200);
  };

  const startCronSimulation = () => {
    if (simulating) return;
    setSimulating(true);
    setActiveFlow('cron');
    
    setSimulatorTasks([
      { id: 't-cron-1', name: 'VMS Sync: Fieldglass & Beeline', type: 'sync', status: 'pending', time: 'Triggered', color: 'var(--warn)' }
    ]);
    
    const logs = [];
    const addLog = (sender, text) => {
      const nowStr = new Date().toLocaleTimeString();
      logs.push({ time: nowStr, sender, text });
      setSimLogs([...logs]);
    };
    
    addLog('system', '⏰ Scheduled Timer Alert: VMS Sync Cron pattern fired.');
    
    setTimeout(() => {
      addLog('vms_agent', '🤖 VMS Agent claimed task t-cron-1. Simulating portal sessions to grab new requisitions...');
      setSimulatorTasks(prev => [
        { ...prev[0], status: 'running', time: 'Syncing...' }
      ]);
      
      setTimeout(() => {
        addLog('vms_agent', '🌐 Logged in to Fieldglass. Scraped 3 new roles. Scraped 1 role from Beeline. Inserting Requisitions...');
        
        setTimeout(() => {
          addLog('postgres_queue', '💾 Inserted 4 new Requisitions into Postgres. Enqueuing Auto-Matching tasks (Tasks t-cron-2 to t-cron-5) for vector comparison...');
          setSimulatorTasks(prev => [
            { ...prev[0], status: 'completed', time: 'Done' },
            { id: 't-cron-2', name: 'Auto-Match: Req #401 (AWS Architect)', type: 'match', status: 'pending', time: 'Queued', color: 'var(--purple)' },
            { id: 't-cron-3', name: 'Auto-Match: Req #402 (Python Dev)', type: 'match', status: 'pending', time: 'Queued', color: 'var(--purple)' }
          ]);
          
          setTimeout(() => {
            addLog('matching_agent', '🤖 Matching Agent picked up Req #401. Scanning candidates table for matching vector profiles...');
            setSimulatorTasks(prev => [
              prev[0],
              { ...prev[1], status: 'running', time: 'Matching...' },
              prev[2]
            ]);
            
            setTimeout(() => {
              addLog('matching_agent', '✅ Auto-Match calculations complete. Saved matches in DB.');
              setSimulatorTasks(prev => [
                prev[0],
                { ...prev[1], status: 'completed', time: 'Match Saved' },
                { ...prev[2], status: 'completed', time: 'Match Saved' }
              ]);
              addLog('system', '🏁 VMS Auto-Sync & Matching simulation resolved.');
              setSimulating(false);
              setActiveFlow(null);
            }, 1500);
            
          }, 1500);
          
        }, 1500);
        
      }, 1800);
      
    }, 1200);
  };

  const selectedNode = BLOCKS[selectedBlock];

  return (
    <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
      
      {/* Dynamic inline styles for the scheduler diagram and animations */}
      <style>{`
        .scheduler-grid {
          display: grid;
          grid-template-columns: 2fr 1fr;
          gap: 1.5rem;
          margin-top: 1.5rem;
        }
        @media (max-width: 1024px) {
          .scheduler-grid {
            grid-template-columns: 1fr;
          }
        }
        
        /* Node visual diagram styles */
        .diagram-board {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 2rem;
          min-height: 580px;
          position: relative;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          overflow: hidden;
          box-shadow: var(--shadow-card);
        }
        
        .diagram-columns {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 1rem;
          position: relative;
          z-index: 2;
          height: 100%;
        }
        @media (max-width: 768px) {
          .diagram-columns {
            grid-template-columns: 1fr;
            gap: 2rem;
            display: flex;
            flex-direction: column;
          }
        }
        
        .diagram-col {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 2.5rem;
        }
        
        .col-header {
          font-size: 0.72rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--text-muted);
          text-align: center;
          margin-bottom: 0.5rem;
          border-bottom: 1px solid var(--border);
          padding-bottom: 0.4rem;
          width: 100%;
        }
        
        /* Card Block styling */
        .block-card {
          width: 100%;
          max-width: 160px;
          background: var(--bg-dark);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          padding: 0.8rem;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
          text-align: center;
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.5rem;
        }
        
        .block-card:hover {
          transform: translateY(-4px);
          border-color: var(--border-active);
          box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }
        
        .block-card.active {
          border-color: var(--active-color, var(--primary));
          background: var(--bg-hover);
          box-shadow: 0 0 15px var(--active-glow, rgba(0,242,254,0.15));
        }
        
        .block-icon-wrapper {
          width: 38px;
          height: 38px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: color-mix(in srgb, var(--active-color, var(--primary)) 12%, transparent);
          border: 1px solid color-mix(in srgb, var(--active-color, var(--primary)) 25%, transparent);
          color: var(--active-color, var(--primary));
          margin-bottom: 0.2rem;
          transition: transform 0.3s;
        }
        .block-card:hover .block-icon-wrapper {
          transform: scale(1.1);
        }
        
        .block-title {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-primary);
        }
        
        .block-badge {
          font-size: 0.65rem;
          font-weight: 500;
          padding: 0.15rem 0.45rem;
          border-radius: 20px;
          margin-top: 0.2rem;
          display: inline-block;
        }
        
        .badge-sleeping {
          background: hsla(210, 10%, 45%, 0.15);
          color: var(--text-secondary);
          border: 1px solid hsla(210, 10%, 45%, 0.3);
        }
        
        .badge-running {
          background: hsla(142, 70%, 50%, 0.15);
          color: var(--success);
          border: 1px solid hsla(142, 70%, 50%, 0.3);
          animation: pulse-badge 1.5s infinite;
        }
        
        .badge-active {
          background: hsla(168, 80%, 50%, 0.15);
          color: var(--accent);
          border: 1px solid hsla(168, 80%, 50%, 0.3);
        }
        
        @keyframes pulse-badge {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        
        /* Floating particles lines SVG overlay */
        .svg-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 1;
        }
        
        .svg-flow-path {
          stroke: var(--border);
          stroke-width: 2;
          fill: none;
          stroke-linecap: round;
        }
        
        .svg-flow-path-active {
          stroke-width: 2;
          fill: none;
          stroke-linecap: round;
          animation: stroke-glow 2s infinite linear;
        }
        
        @keyframes stroke-glow {
          to {
            stroke-dashoffset: -20;
          }
        }
        
        /* Info Sidebar Styles */
        .info-sidebar {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
          box-shadow: var(--shadow-card);
        }
        
        .code-container {
          background: var(--bg-deep);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          padding: 0.85rem;
          font-family: 'Courier New', Courier, monospace;
          font-size: 0.76rem;
          overflow-x: auto;
          color: #a9b7c6;
          max-height: 250px;
          line-height: 1.5;
        }
        
        /* Queue Simulator CSS */
        .queue-sim-grid {
          display: grid;
          grid-template-columns: 1fr 1.2fr;
          gap: 1.5rem;
          margin-top: 1.5rem;
        }
        @media (max-width: 768px) {
          .queue-sim-grid {
            grid-template-columns: 1fr;
          }
        }
        
        .task-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.75rem 1rem;
          background: var(--bg-dark);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          margin-bottom: 0.75rem;
          animation: slideIn 0.3s ease-out;
        }
        
        .log-panel {
          background: #06070b;
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 1.25rem;
          font-family: monospace;
          height: 380px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
          box-shadow: inset 0 2px 8px rgba(0,0,0,0.8);
        }
        
        .log-row {
          display: flex;
          gap: 0.75rem;
          font-size: 0.8rem;
          line-height: 1.5;
          border-bottom: 1px solid rgba(255,255,255,0.02);
          padding-bottom: 0.25rem;
        }
        
        .log-time { color: var(--text-muted); }
        .log-sender { font-weight: bold; color: var(--primary); }
        .log-text { color: var(--text-primary); }
        
        /* Cron Playground */
        .cron-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 1.8rem;
          max-width: 800px;
          margin: 1.5rem auto;
          box-shadow: var(--shadow-card);
        }
        
        .cron-input-group {
          display: flex;
          gap: 0.75rem;
          margin-top: 1rem;
          margin-bottom: 1.5rem;
        }
        
        .cron-timeline-point {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 0.6rem 1rem;
          background: var(--bg-dark);
          border-left: 3px solid var(--accent);
          border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
          margin-bottom: 0.5rem;
        }
      `}</style>

      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Automated Scheduler Architecture</h1>
          <div className="page-subtitle">Interactive block diagram and real-time simulator of recruiter background jobs</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', background: 'hsla(142, 70%, 50%, 0.1)', border: '1px solid hsla(142, 70%, 50%, 0.3)', padding: '0.4rem 0.9rem', borderRadius: '20px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--success)' }}>
          <span className="brand-dot" style={{ background: 'var(--success)', boxShadow: '0 0 8px var(--success)', width: 6, height: 6, borderRadius: '50%' }} />
          Scheduling Engine Active (Production Mode)
        </div>
      </div>

      {/* Tabs */}
      <div className="tab-bar">
        <button className={`tab-btn${activeTab === 'diagram' ? ' active' : ''}`} onClick={() => setActiveTab('diagram')}>
          <Layers size={14} /> Interactive Block Diagram
        </button>
        <button className={`tab-btn${activeTab === 'simulator' ? ' active' : ''}`} onClick={() => setActiveTab('simulator')}>
          <Workflow size={14} /> Task Queue Simulator
        </button>
        <button className={`tab-btn${activeTab === 'cron' ? ' active' : ''}`} onClick={() => setActiveTab('cron')}>
          <Clock size={14} /> Cron Playground
        </button>
      </div>

      {/* Interactive Diagram Tab */}
      {activeTab === 'diagram' && (
        <div className="scheduler-grid">
          
          {/* Visual block diagram container */}
          <div className="diagram-board">
            
            {/* SVG Connector Lines */}
            <svg className="svg-overlay" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="gradient-primary" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.8" />
                </linearGradient>
                <linearGradient id="gradient-danger" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="var(--danger)" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="var(--warn)" stopOpacity="0.8" />
                </linearGradient>
              </defs>

              {/* Connecting triggers to gateway (Orchestrator) */}
              <path d="M 110,195 L 210,270" className="svg-flow-path" />
              <path d="M 110,335 L 210,270" className="svg-flow-path" />
              <path d="M 110,195 L 210,270" className="svg-flow-path-active" stroke="var(--primary)" strokeDasharray="6,6" />
              <path d="M 110,335 L 210,270" className="svg-flow-path-active" stroke="var(--primary)" strokeDasharray="6,6" />

              {/* Gateway to Central Postgres Queue */}
              <path d="M 330,270 L 400,270" className="svg-flow-path" />
              <path d="M 330,270 L 400,270" className="svg-flow-path-active" stroke="var(--accent)" strokeDasharray="6,6" />

              {/* Queue to Agents (Split Paths) */}
              <path d="M 500,270 L 590,140" className="svg-flow-path" />
              <path d="M 500,270 L 590,270" className="svg-flow-path" />
              <path d="M 500,270 L 590,400" className="svg-flow-path" />
              <path d="M 500,270 L 590,140" className="svg-flow-path-active" stroke="var(--purple)" strokeDasharray="6,6" />
              <path d="M 500,270 L 590,270" className="svg-flow-path-active" stroke="var(--purple)" strokeDasharray="6,6" />
              <path d="M 500,270 L 590,400" className="svg-flow-path-active" stroke="var(--purple)" strokeDasharray="6,6" />

              {/* Agents back to Queue (Feedback loop / write results) */}
              <path d="M 590,150 Q 520,180 500,260" className="svg-flow-path" stroke="var(--border)" strokeDasharray="4,4" />
              <path d="M 590,410 Q 520,380 500,280" className="svg-flow-path" stroke="var(--border)" strokeDasharray="4,4" />

              {/* Agents & queue to external APIs (MS Graph) */}
              <path d="M 710,140 Q 750,200 790,250" className="svg-flow-path" />
              <path d="M 710,400 Q 750,340 790,290" className="svg-flow-path" />
              <path d="M 710,400 Q 750,340 790,290" className="svg-flow-path-active" stroke="var(--accent)" strokeDasharray="6,6" />
            </svg>

            {/* Columns structure */}
            <div className="diagram-columns">
              
              {/* Column 1: Triggers */}
              <div className="diagram-col">
                <div className="col-header">1. Triggers</div>
                
                {/* Node: VMS Sync Clock */}
                <div 
                  className={`block-card${selectedBlock === 'vms_cron' ? ' active' : ''}`}
                  onClick={() => setSelectedBlock('vms_cron')}
                  style={{ '--active-color': BLOCKS.vms_cron.color }}
                >
                  <div className="block-icon-wrapper"><Clock size={18} /></div>
                  <div className="block-title">{BLOCKS.vms_cron.title}</div>
                  <span className="block-badge badge-sleeping">1 Hr Polling</span>
                </div>
                
                {/* Node: Resume Ingestion Upload */}
                <div 
                  className={`block-card${selectedBlock === 'resume_upload' ? ' active' : ''}`}
                  onClick={() => setSelectedBlock('resume_upload')}
                  style={{ '--active-color': BLOCKS.resume_upload.color }}
                >
                  <div className="block-icon-wrapper"><UploadIcon size={18} /></div>
                  <div className="block-title">{BLOCKS.resume_upload.title}</div>
                  <span className="block-badge badge-active">Instant Event</span>
                </div>
              </div>

              {/* Column 2: Gateway */}
              <div className="diagram-col">
                <div className="col-header">2. Gateway</div>
                
                {/* Node: Orchestrator */}
                <div 
                  className={`block-card${selectedBlock === 'orchestrator' ? ' active' : ''}`}
                  onClick={() => setSelectedBlock('orchestrator')}
                  style={{ '--active-color': BLOCKS.orchestrator.color, marginSelf: 'center' }}
                >
                  <div className="block-icon-wrapper"><Server size={18} /></div>
                  <div className="block-title">{BLOCKS.orchestrator.title}</div>
                  <span className="block-badge badge-running">FastAPI</span>
                </div>
              </div>

              {/* Column 3: Database Store */}
              <div className="diagram-col">
                <div className="col-header">3. Queue Hub</div>
                
                {/* Node: Postgres DB */}
                <div 
                  className={`block-card${selectedBlock === 'postgres_queue' ? ' active' : ''}`}
                  onClick={() => setSelectedBlock('postgres_queue')}
                  style={{ '--active-color': BLOCKS.postgres_queue.color }}
                >
                  <div className="block-icon-wrapper"><Database size={18} /></div>
                  <div className="block-title">{BLOCKS.postgres_queue.title}</div>
                  <span className="block-badge badge-active">PGVector Queue</span>
                </div>
              </div>

              {/* Column 4: Agents */}
              <div className="diagram-col" style={{ gap: '1.2rem' }}>
                <div className="col-header">4. Agent Workers</div>
                
                {/* Node: VMS Sync Worker */}
                <div 
                  className={`block-card${selectedBlock === 'vms_agent' ? ' active' : ''}`}
                  onClick={() => setSelectedBlock('vms_agent')}
                  style={{ '--active-color': BLOCKS.vms_agent.color, padding: '0.6rem' }}
                >
                  <div className="block-icon-wrapper" style={{ width: 30, height: 30 }}><Cpu size={14} /></div>
                  <div className="block-title" style={{ fontSize: '0.8rem' }}>VMS Sync</div>
                  <span className="block-badge badge-sleeping" style={{ fontSize: '0.6rem' }}>1hr Cycle</span>
                </div>

                {/* Node: Matching Agent */}
                <div 
                  className={`block-card${selectedBlock === 'matching_agent' ? ' active' : ''}`}
                  onClick={() => setSelectedBlock('matching_agent')}
                  style={{ '--active-color': BLOCKS.matching_agent.color, padding: '0.6rem' }}
                >
                  <div className="block-icon-wrapper" style={{ width: 30, height: 30 }}><Cpu size={14} /></div>
                  <div className="block-title" style={{ fontSize: '0.8rem' }}>AI Matcher</div>
                  <span className="block-badge badge-running" style={{ fontSize: '0.6rem' }}>Continuous</span>
                </div>

                {/* Node: Self Healing */}
                <div 
                  className={`block-card${selectedBlock === 'self_healing_agent' ? ' active' : ''}`}
                  onClick={() => setSelectedBlock('self_healing_agent')}
                  style={{ '--active-color': BLOCKS.self_healing_agent.color, padding: '0.6rem' }}
                >
                  <div className="block-icon-wrapper" style={{ width: 30, height: 30 }}><Cpu size={14} /></div>
                  <div className="block-title" style={{ fontSize: '0.8rem' }}>Self-Healing</div>
                  <span className="block-badge badge-running" style={{ fontSize: '0.6rem' }}>5 Mins loop</span>
                </div>
              </div>

              {/* Column 5: Outputs */}
              <div className="diagram-col">
                <div className="col-header">5. Outputs</div>
                
                {/* Node: MS Graph */}
                <div 
                  className={`block-card${selectedBlock === 'ms_graph' ? ' active' : ''}`}
                  onClick={() => setSelectedBlock('ms_graph')}
                  style={{ '--active-color': BLOCKS.ms_graph.color }}
                >
                  <div className="block-icon-wrapper"><Mail size={18} /></div>
                  <div className="block-title">{BLOCKS.ms_graph.title}</div>
                  <span className="block-badge badge-active">SMTP Alerts</span>
                </div>
              </div>

            </div>

            {/* Footnote instruction */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem', zIndex: 2 }}>
              <Eye size={12} />
              <span>Click on any architectural block to inspect its scheduling properties, runtime details, and real code.</span>
            </div>
          </div>

          {/* Info Sidebar */}
          <div className="info-sidebar">
            <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center' }}>
              <div style={{ width: 42, height: 42, borderRadius: 'var(--radius-sm)', background: `color-mix(in srgb, ${selectedNode.color} 15%, transparent)`, border: `1px solid ${selectedNode.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: selectedNode.color }}>
                {React.createElement(selectedNode.icon, { size: 20 })}
              </div>
              <div>
                <h3 style={{ fontSize: '1.1rem', color: 'var(--text-primary)' }}>{selectedNode.title}</h3>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: selectedNode.color, textTransform: 'uppercase' }}>{selectedNode.interval}</span>
              </div>
            </div>

            <div>
              <h4 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.3rem' }}>Description</h4>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>{selectedNode.description}</p>
            </div>

            <div>
              <h4 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.3rem' }}>Implementation Details</h4>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>{selectedNode.details}</p>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <h4 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>Code Implementation</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  <Code size={11} /> Source
                </div>
              </div>
              <div className="code-container">
                <pre>{selectedNode.code}</pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Task Queue Simulator Tab */}
      {activeTab === 'simulator' && (
        <div>
          <div className="data-card" style={{ marginBottom: '1.5rem', background: 'linear-gradient(135deg, var(--bg-card) 0%, rgba(20, 25, 40, 0.5) 100%)' }}>
            <h3 style={{ fontSize: '1.1rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <Sparkles size={16} color="var(--accent)" /> System Workflow Simulator
            </h3>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', maxWidth: '800px', marginBottom: '1.25rem' }}>
              Trigger a simulated event flow to watch how the background scheduling queue locks tasks, executes worker routines, logs steps, and integrates with third-party APIs.
            </p>
            <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={startResumeSimulation} disabled={simulating}>
                {simulating && activeFlow === 'resume' ? <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={14} />}
                Simulate Resume Ingestion (Webhook Event)
              </button>
              <button className="btn btn-ghost" onClick={startCronSimulation} disabled={simulating}>
                {simulating && activeFlow === 'cron' ? <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={14} />}
                Simulate Scheduled VMS Sync (Cron Trigger)
              </button>
            </div>
          </div>

          <div className="queue-sim-grid">
            
            {/* Live Queue state */}
            <div>
              <h3 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <ListTodo size={15} color="var(--primary)" /> Database Queue State
              </h3>
              <div>
                {simulatorTasks.map(task => (
                  <div key={task.id} className="task-row" style={{ borderLeft: `3px solid ${task.color}` }}>
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{task.name}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>ID: {task.id} · Type: {task.type}</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className={`badge ${task.status === 'completed' ? 'badge-green' : task.status === 'running' ? 'badge-blue' : 'badge-gray'}`} style={{ fontSize: '0.7rem' }}>
                        {task.status}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{task.time}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Daemon Logs */}
            <div>
              <h3 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Code size={15} color="var(--accent)" /> Real-Time Scheduler Daemon Logs
              </h3>
              <div className="log-panel">
                {simLogs.map((log, index) => (
                  <div key={index} className="log-row">
                    <span className="log-time">[{log.time}]</span>
                    <span className="log-sender">{log.sender}:</span>
                    <span className="log-text">{log.text}</span>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Cron Playground Tab */}
      {activeTab === 'cron' && (
        <div className="cron-card">
          <h3 style={{ fontSize: '1.1rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
            <Clock size={16} color="var(--warn)" /> Cron Trigger Planner
          </h3>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
            Choose a cron pattern or enter a standard expression to see how the background agent queue evaluates future runtimes.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem', marginBottom: '1.25rem' }}>
            {[
              { label: 'Every 5 Minutes', pattern: '*/5 * * * *' },
              { label: 'Every 15 Minutes', pattern: '*/15 * * * *' },
              { label: 'Hourly (at minute 0)', pattern: '0 * * * *' },
              { label: 'Daily (at midnight)', pattern: '0 0 * * *' }
            ].map(preset => (
              <button 
                key={preset.pattern}
                type="button" 
                className={`btn ${cronInput === preset.pattern ? 'btn-primary' : 'btn-ghost'}`}
                style={{ fontSize: '0.78rem', padding: '0.4rem' }}
                onClick={() => setCronInput(preset.pattern)}
              >
                {preset.label}
              </button>
            ))}
          </div>

          <div className="cron-input-group">
            <input 
              type="text" 
              className="search-input" 
              style={{ flex: 1, fontFamily: 'monospace' }} 
              value={cronInput}
              onChange={e => setCronInput(e.target.value)}
              placeholder="e.g. */10 * * * *"
            />
            <button className="btn btn-primary" onClick={() => calculateCronTimes(cronInput)}>
              <RefreshCw size={14} /> Calculate
            </button>
          </div>

          <div style={{ background: 'var(--bg-dark)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '1.25rem', marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Evaluated Schedule Description</div>
            <strong style={{ color: 'var(--accent)', fontSize: '1.05rem' }}>{cronSummary}</strong>
          </div>

          <div>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Simulated Next 5 Runs</h4>
            {simulatedTimes.map((time, idx) => (
              <div key={idx} className="cron-timeline-point">
                <div style={{ width: 20, height: 20, borderRadius: '50%', background: 'hsla(168, 80%, 50%, 0.1)', border: '1px solid var(--accent)', display: 'flex', alignItems: 'center', justifyText: 'center', fontSize: '0.7rem', color: 'var(--accent)', fontWeight: 'bold', justifyContent: 'center' }}>
                  {idx + 1}
                </div>
                <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>{time}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                  {idx === 0 ? 'Next execution' : `Execution +${idx * 5} intervals`}
                </div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: '1.5rem', padding: '1rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
              <Code size={13} color="var(--primary)" /> How scheduling is checked in the loop:
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
              For standard Node.js/Python daemons, scheduling is verified by parsing the cron string using libraries like <code style={{ color: 'var(--warn)' }}>cron-parser</code>, evaluating the current time, and querying the database queue for tasks due for execution.
            </p>
          </div>

        </div>
      )}

    </div>
  );
}
