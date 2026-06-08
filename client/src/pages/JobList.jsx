import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { MapPin, Building, Tag, Search, RefreshCw, Briefcase, XCircle, ArrowRight, Calendar } from 'lucide-react';

const ORCHESTRATOR = 'https://westley-agents.kindtree-748f04e0.centralus.azurecontainerapps.io';

export default function JobList() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  const fetchJobs = async () => {
    setLoading(true); setError(null);
    try {
      // Try orchestrator first, fall back to local proxy
      const res = await axios.get(`${ORCHESTRATOR}/requisitions?status=open&limit=100`).catch(() =>
        axios.get('/api/jobs')
      );
      setJobs(res.data);
    } catch (err) {
      setError(err.message);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchJobs(); }, []);

  const filtered = jobs.filter(j => {
    if (!search) return true;
    const q = search.toLowerCase();
    const skills = j.skills || j.skills_required || [];
    return (
      (j.title || '').toLowerCase().includes(q) ||
      (j.company || j.client_company || '').toLowerCase().includes(q) ||
      (j.location || '').toLowerCase().includes(q) ||
      skills.some(s => s.toLowerCase().includes(q))
    );
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Open Requisitions</h1>
          <div className="page-subtitle">Active job orders from VMS platforms, ready for matching</div>
        </div>
        <button className="btn btn-ghost" onClick={fetchJobs} disabled={loading}>
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      <div className="filter-bar">
        <div className="search-wrapper">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search title, company, skill…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          {filtered.length} {filtered.length === 1 ? 'role' : 'roles'}
        </span>
      </div>

      {loading ? (
        <div className="loading-state"><div className="spinner" /><span>Loading jobs…</span></div>
      ) : error ? (
        <div className="empty-state">
          <div className="empty-icon"><XCircle size={24} /></div>
          <strong>Failed to load</strong>
          <span>{error}</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><Briefcase size={24} /></div>
          <strong>No jobs found</strong>
          <span>{search ? 'Try a different search.' : 'Check back soon — agents are scraping VMS platforms.'}</span>
        </div>
      ) : (
        <div className="cards-grid">
          {filtered.map((job, i) => {
            const skills = job.skills || job.skills_required || [];
            const company = job.company || job.client_company;
            const platform = job.vms_platform;
            return (
              <div key={job.id} className="data-card" style={{ animationDelay: `${i * 0.04}s` }}>
                <div className="card-header">
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Link to={`/jobs/${job.id}`} style={{ textDecoration: 'none' }}>
                      <div className="card-title" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--primary)' }}>
                        {job.title}
                      </div>
                    </Link>
                    {company && <div className="card-subtitle">{company}</div>}
                  </div>
                  {platform && <span className="badge badge-blue">{platform}</span>}
                </div>
                <div className="card-body">
                  {job.location && (
                    <div className="card-meta-row"><MapPin size={13} />{job.location}</div>
                  )}
                  {job.job_type && (
                    <div className="card-meta-row"><Briefcase size={13} />{job.job_type}</div>
                  )}
                  {job.bill_rate_max && (
                    <div className="card-meta-row" style={{ color: 'var(--success)' }}>
                      <Tag size={13} /> Up to ${job.bill_rate_max}/hr
                    </div>
                  )}
                </div>
                {skills.length > 0 && (
                  <div className="skills-list">
                    {skills.slice(0, 5).map((s, i) => <span key={i} className="skill-tag">{s}</span>)}
                    {skills.length > 5 && <span className="skill-tag">+{skills.length - 5}</span>}
                  </div>
                )}
                <div className="card-footer">
                  {job.created_at && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <Calendar size={12} />
                      {new Date(job.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </div>
                  )}
                  <Link to={`/jobs/${job.id}`} className="btn btn-ghost btn-sm" style={{ padding: '0.3rem 0.7rem' }}>
                    Details <ArrowRight size={13} />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
