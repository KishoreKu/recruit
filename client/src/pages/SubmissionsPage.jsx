import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Send, User, Briefcase, DollarSign, Clock, Search, RefreshCw,
  CheckCircle, XCircle, AlertCircle, Activity, Calendar
} from 'lucide-react';

const ORCHESTRATOR = 'https://westley-agents.kindtree-748f04e0.centralus.azurecontainerapps.io';

function getStatusBadge(status) {
  const map = {
    submitted:  { cls: 'badge-blue',   icon: Send,          label: 'Submitted' },
    accepted:   { cls: 'badge-green',  icon: CheckCircle,   label: 'Accepted' },
    rejected:   { cls: 'badge-red',    icon: XCircle,       label: 'Rejected' },
    interview:  { cls: 'badge-purple', icon: User,          label: 'Interview' },
    pending:    { cls: 'badge-amber',  icon: AlertCircle,   label: 'Pending' },
    placed:     { cls: 'badge-green',  icon: CheckCircle,   label: 'Placed' },
  };
  const s = map[status] || { cls: 'badge-gray', icon: Activity, label: status };
  const Icon = s.icon;
  return <span className={`badge ${s.cls}`}><Icon size={11} />{s.label}</span>;
}

function getPlatformBadge(platform) {
  const colors = {
    beeline:    'badge-blue',
    fieldglass: 'badge-purple',
    iqnavigator:'badge-amber',
    workday:    'badge-green',
    coupa:      'badge-red',
  };
  const cls = colors[(platform || '').toLowerCase()] || 'badge-gray';
  return <span className={`badge ${cls}`}>{platform || 'Unknown'}</span>;
}

export default function SubmissionsPage() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [view, setView] = useState('table'); // 'table' | 'cards'

  const fetchSubmissions = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${ORCHESTRATOR}/submissions?limit=100`);
      setSubmissions(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSubmissions(); }, []);

  const filtered = submissions.filter(s => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (s.candidate || '').toLowerCase().includes(q) ||
      (s.job_title || '').toLowerCase().includes(q) ||
      (s.vms_platform || '').toLowerCase().includes(q) ||
      (s.status || '').toLowerCase().includes(q)
    );
  });

  // Stats
  const statuses = ['submitted', 'accepted', 'rejected', 'interview', 'placed'];
  const statusCounts = Object.fromEntries(statuses.map(st => [st, submissions.filter(s => s.status === st).length]));

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Submissions</h1>
          <div className="page-subtitle">AI-generated candidate submissions to VMS platforms</div>
        </div>
        <button className="btn btn-ghost" onClick={fetchSubmissions} disabled={loading}>
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="stats-bar">
        <div className="stat-card" style={{ '--stat-color': 'var(--primary)' }}>
          <div className="stat-label">Total</div>
          <div className="stat-value">{submissions.length}</div>
          <Send size={32} className="stat-icon" />
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--success)' }}>
          <div className="stat-label">Accepted</div>
          <div className="stat-value">{statusCounts.accepted + statusCounts.placed}</div>
          <CheckCircle size={32} className="stat-icon" />
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--purple)' }}>
          <div className="stat-label">Interviews</div>
          <div className="stat-value">{statusCounts.interview}</div>
          <User size={32} className="stat-icon" />
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--danger)' }}>
          <div className="stat-label">Rejected</div>
          <div className="stat-value">{statusCounts.rejected}</div>
          <XCircle size={32} className="stat-icon" />
        </div>
      </div>

      {/* Filter */}
      <div className="filter-bar">
        <div className="search-wrapper">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search candidate, job, platform…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="tab-bar" style={{ marginBottom: 0 }}>
          <button className={`tab-btn${view === 'table' ? ' active' : ''}`} onClick={() => setView('table')}>Table</button>
          <button className={`tab-btn${view === 'cards' ? ' active' : ''}`} onClick={() => setView('cards')}>Cards</button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner" />
          <span>Loading submissions…</span>
        </div>
      ) : error ? (
        <div className="empty-state">
          <div className="empty-icon"><XCircle size={24} /></div>
          <strong>Failed to load</strong>
          <span>{error}</span>
          <button className="btn btn-ghost btn-sm" onClick={fetchSubmissions}>Try again</button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><Send size={24} /></div>
          <strong>No submissions yet</strong>
          <span>Submissions will appear here once the matching agent runs.</span>
        </div>
      ) : view === 'table' ? (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Job Title</th>
                <th>Platform</th>
                <th>Status</th>
                <th>Bill Rate</th>
                <th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr key={s.id} style={{ animationDelay: `${i * 0.03}s` }}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <div style={{
                        width: 28, height: 28,
                        borderRadius: 6,
                        background: 'var(--primary-dim)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '0.7rem', fontWeight: 700, color: 'var(--primary-glow)',
                        flexShrink: 0,
                      }}>
                        {(s.candidate || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.875rem' }}>{s.candidate}</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{s.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Briefcase size={13} style={{ color: 'var(--text-muted)' }} />
                      {s.job_title || '—'}
                    </div>
                  </td>
                  <td>{getPlatformBadge(s.vms_platform)}</td>
                  <td>{getStatusBadge(s.status)}</td>
                  <td>
                    {s.bill_rate_submitted
                      ? <span style={{ color: 'var(--success)', fontWeight: 600 }}>${s.bill_rate_submitted}/hr</span>
                      : <span style={{ color: 'var(--text-muted)' }}>—</span>
                    }
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Calendar size={12} />
                      {new Date(s.submitted_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="cards-grid">
          {filtered.map((s, i) => (
            <div key={s.id} className="data-card" style={{ animationDelay: `${i * 0.05}s` }}>
              <div className="card-header">
                <div>
                  <div className="card-title">{s.candidate}</div>
                  <div className="card-subtitle">{s.email}</div>
                </div>
                {getStatusBadge(s.status)}
              </div>
              <div className="card-body">
                <div className="card-meta-row"><Briefcase size={13} />{s.job_title || 'Unknown Role'}</div>
                <div className="card-meta-row">
                  <Activity size={13} />
                  {s.vms_platform || 'Unknown Platform'}
                </div>
                {s.bill_rate_submitted && (
                  <div className="card-meta-row">
                    <DollarSign size={13} />
                    <strong style={{ color: 'var(--success)' }}>${s.bill_rate_submitted}/hr</strong>
                  </div>
                )}
              </div>
              <div className="card-footer">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <Calendar size={12} />
                  {new Date(s.submitted_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </div>
                {getPlatformBadge(s.vms_platform)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
