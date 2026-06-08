import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Users, MapPin, Briefcase, Clock, Star, Search, RefreshCw,
  Phone, Mail, CheckCircle, XCircle, Calendar
} from 'lucide-react';

const ORCHESTRATOR = 'https://westley-agents.kindtree-748f04e0.centralus.azurecontainerapps.io';

function getInitials(name = '') {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
}

function getStatusBadge(status) {
  const map = {
    active:      { cls: 'badge-green',  label: 'Active' },
    placed:      { cls: 'badge-blue',   label: 'Placed' },
    inactive:    { cls: 'badge-gray',   label: 'Inactive' },
    blacklisted: { cls: 'badge-red',    label: 'Blacklisted' },
  };
  const s = map[status] || { cls: 'badge-gray', label: status };
  return <span className={`badge ${s.cls}`}>{s.label}</span>;
}

function CandidateCard({ candidate, index }) {
  const [expanded, setExpanded] = useState(false);
  const skills = candidate.skills || [];
  const visibleSkills = expanded ? skills : skills.slice(0, 5);

  return (
    <div className="data-card" style={{ animationDelay: `${index * 0.05}s` }}>
      <div className="card-header">
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flex: 1, minWidth: 0 }}>
          <div className="card-avatar">
            {getInitials(candidate.full_name)}
          </div>
          <div style={{ minWidth: 0 }}>
            <div className="card-title" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {candidate.full_name || 'Unknown Candidate'}
            </div>
            <div className="card-subtitle">{candidate.current_title || 'IT Professional'}</div>
          </div>
        </div>
        {getStatusBadge(candidate.status)}
      </div>

      <div className="card-body">
        {candidate.email && (
          <div className="card-meta-row">
            <Mail size={13} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {candidate.email}
            </span>
          </div>
        )}
        {candidate.phone && (
          <div className="card-meta-row">
            <Phone size={13} />
            <span>{candidate.phone}</span>
          </div>
        )}
        {candidate.location && (
          <div className="card-meta-row">
            <MapPin size={13} />
            <span>{candidate.location}</span>
          </div>
        )}
        {candidate.experience_years != null && (
          <div className="card-meta-row">
            <Star size={13} />
            <span>{candidate.experience_years} years experience</span>
          </div>
        )}
      </div>

      {skills.length > 0 && (
        <div>
          <div className="skills-list">
            {visibleSkills.map((s, i) => (
              <span key={i} className="skill-tag">{s}</span>
            ))}
            {skills.length > 5 && (
              <button
                onClick={() => setExpanded(!expanded)}
                style={{ background: 'none', border: 'none', color: 'var(--primary)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600, padding: '0.15rem 0.3rem' }}
              >
                {expanded ? 'less' : `+${skills.length - 5} more`}
              </button>
            )}
          </div>
        </div>
      )}

      <div className="card-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <Calendar size={12} />
          {new Date(candidate.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </div>
        <span className={`badge ${candidate.rtr_given ? 'badge-green' : 'badge-amber'}`}>
          {candidate.rtr_given ? <><CheckCircle size={11} /> RTR ✓</> : <><XCircle size={11} /> No RTR</>}
        </span>
      </div>
    </div>
  );
}

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');

  const fetchCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${ORCHESTRATOR}/candidates?status=${statusFilter}&limit=100`);
      setCandidates(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCandidates(); }, [statusFilter]);

  const filtered = candidates.filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (c.full_name || '').toLowerCase().includes(q) ||
      (c.email || '').toLowerCase().includes(q) ||
      (c.current_title || '').toLowerCase().includes(q) ||
      (c.location || '').toLowerCase().includes(q) ||
      (c.skills || []).some(s => s.toLowerCase().includes(q))
    );
  });

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Candidates</h1>
          <div className="page-subtitle">AI-parsed candidate profiles from resume ingestion</div>
        </div>
        <button className="btn btn-ghost" onClick={fetchCandidates} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'spinning' : ''} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="stats-bar">
        <div className="stat-card" style={{ '--stat-color': 'var(--primary)' }}>
          <div className="stat-label">Total Shown</div>
          <div className="stat-value">{candidates.length}</div>
          <Users size={32} className="stat-icon" />
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--success)' }}>
          <div className="stat-label">With RTR</div>
          <div className="stat-value">{candidates.filter(c => c.rtr_given).length}</div>
          <CheckCircle size={32} className="stat-icon" />
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--warn)' }}>
          <div className="stat-label">No RTR Yet</div>
          <div className="stat-value">{candidates.filter(c => !c.rtr_given).length}</div>
          <XCircle size={32} className="stat-icon" />
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--accent)' }}>
          <div className="stat-label">Filtered</div>
          <div className="stat-value">{filtered.length}</div>
          <Search size={32} className="stat-icon" />
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <div className="search-wrapper">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search by name, skill, location…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="tab-bar" style={{ marginBottom: 0 }}>
          {['active', 'placed', 'inactive'].map(s => (
            <button
              key={s}
              className={`tab-btn${statusFilter === s ? ' active' : ''}`}
              onClick={() => setStatusFilter(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner" />
          <span>Loading candidates…</span>
        </div>
      ) : error ? (
        <div className="empty-state">
          <div className="empty-icon"><XCircle size={24} /></div>
          <strong>Failed to load</strong>
          <span>{error}</span>
          <button className="btn btn-ghost btn-sm" onClick={fetchCandidates}>Try again</button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><Users size={24} /></div>
          <strong>No candidates found</strong>
          <span>{search ? 'Try a different search term.' : 'Submit a resume to get started.'}</span>
        </div>
      ) : (
        <div className="cards-grid">
          {filtered.map((c, i) => (
            <CandidateCard key={c.id} candidate={c} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
