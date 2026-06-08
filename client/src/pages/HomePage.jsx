import React from 'react';
import { Link } from 'react-router-dom';
import { Users, Briefcase, Send, BrainCircuit, ArrowRight, Zap, Shield, TrendingUp } from 'lucide-react';

const features = [
  {
    icon: BrainCircuit,
    color: 'var(--primary)',
    title: 'AI-Powered Matching',
    desc: 'Gemini 2.0 Flash intelligently matches candidates to requisitions using semantic similarity and skill analysis.',
  },
  {
    icon: Zap,
    color: 'var(--accent)',
    title: 'Autonomous Agents',
    desc: 'Background agents continuously process resumes, scrape VMS platforms, and submit candidates around the clock.',
  },
  {
    icon: Shield,
    color: 'var(--purple)',
    title: 'RTR Compliance',
    desc: 'Right-to-represent validation is tracked for every candidate submission, ensuring regulatory compliance.',
  },
  {
    icon: TrendingUp,
    color: 'var(--warn)',
    title: 'Real-Time Pipeline',
    desc: 'Watch your placement pipeline update live — from resume ingestion to client submission in minutes.',
  },
];

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <div className="hero">
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'hsla(220, 90%, 60%, 0.1)',
            border: '1px solid hsla(220, 90%, 60%, 0.25)',
            borderRadius: '20px',
            padding: '0.35rem 1rem',
            fontSize: '0.8rem',
            fontWeight: 600,
            color: 'var(--primary)',
            marginBottom: '2rem',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}
        >
          <span style={{ width: 6, height: 6, background: 'var(--accent)', borderRadius: '50%', boxShadow: '0 0 8px var(--accent)' }} />
          Agentic Placement System · Live
        </div>
        <h1 className="hero-title">
          Intelligent IT<br />Recruiting, Automated
        </h1>
        <p className="hero-sub">
          Westley Resource uses autonomous AI agents to match candidates to open requisitions,
          submit to VMS platforms, and track your entire pipeline — hands-free.
        </p>
        <div className="hero-actions">
          <Link to="/candidates" className="btn btn-primary" style={{ padding: '0.75rem 1.75rem', fontSize: '0.95rem' }}>
            <Users size={18} /> View Candidates <ArrowRight size={16} />
          </Link>
          <Link to="/jobs" className="btn btn-ghost" style={{ padding: '0.75rem 1.75rem', fontSize: '0.95rem' }}>
            <Briefcase size={18} /> Browse Jobs
          </Link>
        </div>
      </div>

      {/* Quick Nav Cards */}
      <div className="cards-grid" style={{ marginBottom: '3rem' }}>
        {[
          { to: '/candidates', icon: Users, label: 'Candidates', desc: 'Browse active candidate profiles with skills and experience.', color: 'var(--primary)' },
          { to: '/jobs', icon: Briefcase, label: 'Requisitions', desc: 'Open job orders aggregated from VMS platforms.', color: 'var(--accent)' },
          { to: '/submissions', icon: Send, label: 'Submissions', desc: 'Track all AI-generated candidate submissions.', color: 'var(--purple)' },
        ].map(({ to, icon: Icon, label, desc, color }) => (
          <Link
            key={to}
            to={to}
            style={{ textDecoration: 'none' }}
          >
            <div className="data-card" style={{ cursor: 'pointer' }}>
              <div style={{
                width: 48, height: 48,
                borderRadius: 'var(--radius-sm)',
                background: `color-mix(in srgb, ${color} 15%, transparent)`,
                border: `1px solid color-mix(in srgb, ${color} 30%, transparent)`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: '1rem',
                color,
              }}>
                <Icon size={22} />
              </div>
              <div className="card-title">{label}</div>
              <div className="card-subtitle" style={{ marginTop: '0.4rem', lineHeight: 1.5 }}>{desc}</div>
              <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem', color, fontSize: '0.85rem', fontWeight: 600 }}>
                View {label} <ArrowRight size={14} />
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Features */}
      <div style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontFamily: 'Outfit, sans-serif', fontWeight: 700, fontSize: '1.5rem', letterSpacing: '-0.02em', marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
          How It Works
        </h2>
        <div className="cards-grid">
          {features.map(({ icon: Icon, color, title, desc }) => (
            <div key={title} className="data-card">
              <div style={{
                width: 40, height: 40,
                borderRadius: 'var(--radius-sm)',
                background: `color-mix(in srgb, ${color} 12%, transparent)`,
                border: `1px solid color-mix(in srgb, ${color} 25%, transparent)`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: '1rem',
                color,
              }}>
                <Icon size={18} />
              </div>
              <div className="card-title" style={{ fontSize: '1rem' }}>{title}</div>
              <div className="card-subtitle" style={{ marginTop: '0.5rem', lineHeight: 1.6 }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
