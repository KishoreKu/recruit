import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Activity, Briefcase, RefreshCw, Search, MapPin, DollarSign,
  XCircle, Building, Calendar, Plus, Send, CheckCircle,
  AlertCircle, Loader, Tag, X
} from 'lucide-react';

const ORCHESTRATOR = 'https://westley-agents.kindtree-748f04e0.centralus.azurecontainerapps.io';

/* ── Requisitions Tab ──────────────────────────────────────── */
function RequisitionsTab() {
  const [reqs, setReqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('open');

  const fetch = async () => {
    setLoading(true); setError(null);
    try {
      const res = await axios.get(`${ORCHESTRATOR}/requisitions?status=${statusFilter}&limit=100`);
      setReqs(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [statusFilter]);

  const filtered = reqs.filter(r => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (r.title || '').toLowerCase().includes(q) ||
      (r.client_company || '').toLowerCase().includes(q) ||
      (r.location || '').toLowerCase().includes(q) ||
      (r.vms_platform || '').toLowerCase().includes(q) ||
      (r.skills_required || []).some(s => s.toLowerCase().includes(q))
    );
  });

  return (
    <div>
      <div className="filter-bar">
        <div className="search-wrapper">
          <Search size={15} className="search-icon" />
          <input type="text" className="search-input" placeholder="Search title, company, skills…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="tab-bar" style={{ marginBottom: 0 }}>
          {['open', 'closed', 'on_hold'].map(s => (
            <button key={s} className={`tab-btn${statusFilter === s ? ' active' : ''}`} onClick={() => setStatusFilter(s)}>
              {s.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </button>
          ))}
        </div>
        <button className="btn btn-ghost btn-sm" onClick={fetch}><RefreshCw size={14} /></button>
      </div>

      {loading ? (
        <div className="loading-state"><div className="spinner" /><span>Loading requisitions…</span></div>
      ) : error ? (
        <div className="empty-state"><div className="empty-icon"><XCircle size={24} /></div><strong>{error}</strong></div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><Briefcase size={24} /></div>
          <strong>No {statusFilter} requisitions</strong>
          <span>Use the "Post Job" tab to add your first requisition.</span>
        </div>
      ) : (
        <div className="cards-grid">
          {filtered.map((r, i) => (
            <div key={r.id} className="data-card" style={{ animationDelay: `${i * 0.04}s` }}>
              <div className="card-header">
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="card-title" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.title}</div>
                  <div className="card-subtitle">{r.client_company}</div>
                </div>
                <span className={`badge ${r.status === 'open' ? 'badge-green' : 'badge-gray'}`}>{r.status}</span>
              </div>
              <div className="card-body">
                {r.location && <div className="card-meta-row"><MapPin size={13} />{r.location}</div>}
                {r.vms_platform && <div className="card-meta-row"><Building size={13} />{r.vms_platform}</div>}
                {r.job_type && <div className="card-meta-row"><Briefcase size={13} />{r.job_type}</div>}
                {r.bill_rate_max && (
                  <div className="card-meta-row">
                    <DollarSign size={13} />
                    <strong style={{ color: 'var(--success)' }}>Up to ${r.bill_rate_max}/hr</strong>
                  </div>
                )}
              </div>
              {(r.skills_required || []).length > 0 && (
                <div className="skills-list">
                  {r.skills_required.slice(0, 6).map((s, i) => <span key={i} className="skill-tag">{s}</span>)}
                  {r.skills_required.length > 6 && <span className="skill-tag">+{r.skills_required.length - 6}</span>}
                </div>
              )}
              <div className="card-footer">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <Calendar size={12} />
                  {new Date(r.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Post Job Tab ──────────────────────────────────────────── */
const PLATFORMS = ['manual', 'Beeline', 'Fieldglass', 'IQNavigator', 'Workday', 'Coupa', 'Ariba', 'Other'];
const JOB_TYPES = ['Contract', 'Contract-to-Hire', 'Full-Time', 'Part-Time'];

const SAMPLE_JOBS = [
  {
    title: 'Senior Cloud Engineer (AWS)',
    client_company: 'Accenture Federal Services',
    description: 'Looking for an experienced AWS Cloud Engineer to architect and manage cloud infrastructure for a federal client. Must have experience with EC2, S3, RDS, Lambda, and CloudFormation.',
    skills_required: ['AWS', 'Terraform', 'Python', 'Kubernetes', 'CI/CD', 'CloudFormation'],
    location: 'Remote / Washington DC',
    job_type: 'Contract',
    bill_rate_max: 95,
    vms_platform: 'Beeline',
  },
  {
    title: 'Data Engineer - Azure Databricks',
    client_company: 'Deloitte Consulting',
    description: 'Senior Data Engineer needed to build and optimize Azure-based data pipelines using Databricks and PySpark. Will work on large-scale data lake architecture.',
    skills_required: ['Azure', 'Databricks', 'PySpark', 'Python', 'SQL', 'Delta Lake'],
    location: 'Chicago, IL (Hybrid)',
    job_type: 'Contract',
    bill_rate_max: 85,
    vms_platform: 'Fieldglass',
  },
  {
    title: 'Full Stack Developer (React / Node)',
    client_company: 'Capital One',
    description: 'Full Stack Developer to build internal financial tools. React frontend, Node.js backend, PostgreSQL database. Experience with TypeScript required.',
    skills_required: ['React', 'Node.js', 'TypeScript', 'PostgreSQL', 'REST APIs', 'Git'],
    location: 'McLean, VA (Hybrid)',
    job_type: 'Contract-to-Hire',
    bill_rate_max: 75,
    vms_platform: 'Workday',
  },
];

function SkillInput({ skills, setSkills }) {
  const [input, setInput] = useState('');

  const add = (value) => {
    const trimmed = value.trim().replace(/,+$/, '');
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
    }
    setInput('');
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      add(input);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <input
          type="text"
          className="search-input"
          style={{ flex: 1 }}
          placeholder="Type skill and press Enter or comma…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          onBlur={() => input.trim() && add(input)}
        />
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => add(input)}>
          <Plus size={14} /> Add
        </button>
      </div>
      {skills.length > 0 && (
        <div className="skills-list">
          {skills.map((s, i) => (
            <span key={i} className="skill-tag" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', cursor: 'default' }}>
              {s}
              <X size={11} style={{ cursor: 'pointer', opacity: 0.6 }} onClick={() => setSkills(skills.filter((_, j) => j !== i))} />
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

const FIELD_STYLE = {
  width: '100%',
  padding: '0.65rem 1rem',
  background: 'var(--bg-dark)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text-primary)',
  fontSize: '0.875rem',
  outline: 'none',
  fontFamily: 'inherit',
  transition: 'border-color 0.2s',
};

const LABEL_STYLE = {
  display: 'block',
  fontSize: '0.78rem',
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: 'var(--text-muted)',
  marginBottom: '0.4rem',
};

function PostJobTab({ onJobPosted }) {
  const emptyForm = {
    title: '', client_company: '', description: '',
    location: '', job_type: 'Contract', bill_rate_max: '',
    vms_platform: 'manual',
  };

  const [form, setForm] = useState(emptyForm);
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [enhancing, setEnhancing] = useState(false);
  const [result, setResult] = useState(null); // { ok, message }

  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }));

  const handleEnhance = async () => {
    if (!form.description) {
      setResult({ ok: false, message: 'Please enter a few bullet points in the description to enhance.' });
      return;
    }
    setEnhancing(true);
    setResult(null);
    try {
      const prompt = `Please enhance this short job description into a professional 2-3 paragraph job listing. Title: ${form.title || 'Unknown'}. Draft: ${form.description}`;
      const res = await axios.post(`${ORCHESTRATOR}/api/ai/generate`, { userPrompt: prompt, system: 'You are an expert technical recruiter. Output only the plain text job description, no markdown formatting.' });
      setForm(f => ({ ...f, description: res.data.text.trim() }));
      setResult({ ok: true, message: '✨ Job description enhanced by AI!' });
    } catch (err) {
      setResult({ ok: false, message: err.response?.data?.detail || err.message });
    } finally {
      setEnhancing(false);
    }
  };

  const loadSample = (sample) => {
    setForm({
      title: sample.title,
      client_company: sample.client_company,
      description: sample.description,
      location: sample.location,
      job_type: sample.job_type,
      bill_rate_max: sample.bill_rate_max,
      vms_platform: sample.vms_platform,
    });
    setSkills(sample.skills_required);
    setResult(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title || !form.client_company || !form.description || !form.location) {
      setResult({ ok: false, message: 'Please fill in all required fields.' });
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const payload = {
        ...form,
        bill_rate_max: form.bill_rate_max ? parseFloat(form.bill_rate_max) : null,
        skills_required: skills,
      };
      const res = await axios.post(`${ORCHESTRATOR}/add-job`, payload);
      setResult({ ok: true, message: `✅ Job posted! Requisition ID: ${res.data.requisition_id}. Matching agent queued.` });
      setForm(emptyForm);
      setSkills([]);
      if (onJobPosted) onJobPosted();
    } catch (err) {
      setResult({ ok: false, message: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Sample Jobs */}
      <div style={{ marginBottom: '1.75rem' }}>
        <div style={{ ...LABEL_STYLE, marginBottom: '0.75rem' }}>Quick-fill with a sample job</div>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {SAMPLE_JOBS.map((j, i) => (
            <button
              key={i}
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => loadSample(j)}
              style={{ fontSize: '0.8rem' }}
            >
              {j.title}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
          {/* Title */}
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={LABEL_STYLE}>Job Title <span style={{ color: 'var(--danger)' }}>*</span></label>
            <input type="text" style={FIELD_STYLE} placeholder="e.g. Senior Cloud Engineer" value={form.title} onChange={set('title')} required />
          </div>

          {/* Company */}
          <div>
            <label style={LABEL_STYLE}>Client Company <span style={{ color: 'var(--danger)' }}>*</span></label>
            <input type="text" style={FIELD_STYLE} placeholder="e.g. Deloitte" value={form.client_company} onChange={set('client_company')} required />
          </div>

          {/* Location */}
          <div>
            <label style={LABEL_STYLE}>Location <span style={{ color: 'var(--danger)' }}>*</span></label>
            <input type="text" style={FIELD_STYLE} placeholder="e.g. Remote / New York, NY" value={form.location} onChange={set('location')} required />
          </div>

          {/* Job Type */}
          <div>
            <label style={LABEL_STYLE}>Job Type</label>
            <select style={{ ...FIELD_STYLE, cursor: 'pointer' }} value={form.job_type} onChange={set('job_type')}>
              {JOB_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          {/* VMS Platform */}
          <div>
            <label style={LABEL_STYLE}>VMS Platform</label>
            <select style={{ ...FIELD_STYLE, cursor: 'pointer' }} value={form.vms_platform} onChange={set('vms_platform')}>
              {PLATFORMS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {/* Bill Rate */}
          <div>
            <label style={LABEL_STYLE}>Max Bill Rate ($/hr)</label>
            <input type="number" style={FIELD_STYLE} placeholder="e.g. 85" min="0" step="0.5" value={form.bill_rate_max} onChange={set('bill_rate_max')} />
          </div>

          {/* Description */}
          <div style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <label style={{ ...LABEL_STYLE, marginBottom: 0 }}>Job Description <span style={{ color: 'var(--danger)' }}>*</span></label>
              <button 
                type="button" 
                onClick={handleEnhance} 
                disabled={enhancing}
                style={{
                  background: 'linear-gradient(90deg, #4facfe 0%, #00f2fe 100%)',
                  border: 'none', color: '#000', padding: '0.3rem 0.6rem', 
                  borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, 
                  cursor: enhancing ? 'not-allowed' : 'pointer',
                  opacity: enhancing ? 0.7 : 1
                }}
              >
                {enhancing ? '✨ Enhancing...' : '✨ AI Enhance'}
              </button>
            </div>
            <textarea
              style={{ ...FIELD_STYLE, minHeight: '130px', resize: 'vertical', lineHeight: 1.6 }}
              placeholder="Describe the role, responsibilities, and requirements…"
              value={form.description}
              onChange={set('description')}
              required
            />
          </div>

          {/* Skills */}
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={LABEL_STYLE}>Required Skills</label>
            <SkillInput skills={skills} setSkills={setSkills} />
          </div>
        </div>

        {/* Result message */}
        {result && (
          <div style={{
            marginTop: '1.25rem',
            padding: '0.85rem 1.1rem',
            borderRadius: 'var(--radius-sm)',
            background: result.ok ? 'hsla(142, 70%, 50%, 0.1)' : 'hsla(0, 75%, 60%, 0.1)',
            border: `1px solid ${result.ok ? 'hsla(142, 70%, 50%, 0.3)' : 'hsla(0, 75%, 60%, 0.3)'}`,
            color: result.ok ? 'var(--success)' : 'var(--danger)',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.6rem',
          }}>
            {result.ok ? <CheckCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} /> : <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />}
            {result.message}
          </div>
        )}

        {/* Submit */}
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ padding: '0.7rem 1.75rem' }}>
            {loading ? <><Loader size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> Posting…</> : <><Send size={15} /> Post Requisition</>}
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => { setForm(emptyForm); setSkills([]); setResult(null); }}>
            Clear
          </button>
        </div>
      </form>
    </div>
  );
}

/* ── Health Log Tab ────────────────────────────────────────── */
function getHealthDot(level) {
  const map = { ok: 'ok', success: 'ok', succeeded: 'ok', error: 'error', warning: 'warn', warn: 'warn', info: 'info', health_report: 'info' };
  return map[(level || '').toLowerCase()] || 'info';
}

function HealthLogTab() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = async () => {
    setLoading(true); setError(null);
    try {
      const res = await axios.get(`${ORCHESTRATOR}/health-log?limit=100`);
      setLogs(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  if (loading) return <div className="loading-state"><div className="spinner" /><span>Loading logs…</span></div>;
  if (error) return <div className="empty-state"><div className="empty-icon"><XCircle size={24} /></div><strong>{error}</strong></div>;
  if (logs.length === 0) return (
    <div className="empty-state"><div className="empty-icon"><Activity size={24} /></div><strong>No health events recorded</strong></div>
  );

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginBottom: '0.75rem', alignItems: 'center' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{logs.length} events</span>
        <button className="btn btn-ghost btn-sm" onClick={fetch}><RefreshCw size={13} /> Refresh</button>
      </div>
      <div className="table-wrapper">
        {logs.map((log, i) => (
          <div key={log.id} className="health-item" style={{ animationDelay: `${i * 0.02}s` }}>
            <div className={`health-dot ${getHealthDot(log.event_type)}`} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', marginBottom: '0.2rem', flexWrap: 'wrap' }}>
                <span className="health-agent">{log.agent_name}</span>
                <span className={`badge ${log.event_type === 'error' ? 'badge-red' : log.event_type === 'succeeded' ? 'badge-green' : 'badge-blue'}`}
                  style={{ fontSize: '0.65rem', padding: '0.1rem 0.45rem' }}>
                  {log.event_type}
                </span>
              </div>
              <div className="health-msg">{log.message}</div>
            </div>
            <div className="health-time">
              {new Date(log.logged_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Main Dashboard ─────────────────────────────────────────── */
export default function AdminDashboard() {
  const [tab, setTab] = useState('post');

  const tabs = [
    { id: 'post',         label: 'Post Job',      icon: Plus },
    { id: 'requisitions', label: 'Requisitions',  icon: Briefcase },
    { id: 'health',       label: 'Agent Health',  icon: Activity },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Admin Dashboard</h1>
          <div className="page-subtitle">Post requisitions and monitor agent health in real time</div>
        </div>
      </div>

      <div className="tab-bar">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} className={`tab-btn${tab === id ? ' active' : ''}`} onClick={() => setTab(id)}>
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'post'         && <PostJobTab onJobPosted={() => setTab('requisitions')} />}
      {tab === 'requisitions' && <RequisitionsTab />}
      {tab === 'health'       && <HealthLogTab />}
    </div>
  );
}
