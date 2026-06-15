import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Building, DollarSign, Calendar, MessageSquare, User, Mail, Phone } from 'lucide-react';

const ORCHESTRATOR = 'https://westley-agents.kindtree-748f04e0.centralus.azurecontainerapps.io';

const JobDetail = () => {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJob = async () => {
      try {
        const res = await axios.get(`${ORCHESTRATOR}/requisitions/${id}`);
        setJob(res.data);
      } catch (err) {
        console.error('Failed to fetch job detail:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchJob();
  }, [id]);

  if (loading) return <div>Loading...</div>;
  if (!job) return <div>Job not found.</div>;

  return (
    <div>
      <Link to="/jobs" style={{ display: 'inline-flex', alignItems: 'center', marginBottom: '1.5rem', color: '#646cff', textDecoration: 'none' }}>
        <ArrowLeft size={16} style={{ marginRight: '4px' }} /> Back to Jobs
      </Link>

      <div className="job-card" style={{ padding: '2rem' }}>
        <h1 className="job-title" style={{ fontSize: '2rem', marginBottom: '1rem' }}>{job.title}</h1>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Building size={18} style={{ marginRight: '8px' }} /> <strong>Company:</strong>&nbsp;{job.client_company || 'Not Specified'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <MapPin size={18} style={{ marginRight: '8px' }} /> <strong>Location:</strong>&nbsp;{job.location || 'Remote'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <DollarSign size={18} style={{ marginRight: '8px' }} /> <strong>Salary:</strong>&nbsp;{job.bill_rate_max ? `$${job.bill_rate_max}/hr` : 'Competitive'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Calendar size={18} style={{ marginRight: '8px' }} /> <strong>Posted:</strong>&nbsp;{new Date(job.created_at).toLocaleDateString()}
          </div>
          {job.client_contact_name && (
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <User size={18} style={{ marginRight: '8px' }} /> <strong>Contact Name:</strong>&nbsp;{job.client_contact_name}
            </div>
          )}
          {job.client_contact_email && (
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Mail size={18} style={{ marginRight: '8px' }} /> <strong>Contact Email:</strong>&nbsp;{job.client_contact_email}
            </div>
          )}
          {job.client_contact_phone && (
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Phone size={18} style={{ marginRight: '8px' }} /> <strong>Contact Phone:</strong>&nbsp;{job.client_contact_phone}
            </div>
          )}
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h3>Required Skills</h3>
          <div className="job-skills">
            {job.skills_required && job.skills_required.map((skill, index) => (
              <span key={index} className="skill-tag" style={{ fontSize: '1rem', padding: '4px 12px' }}>{skill}</span>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h3>Auto Apply</h3>
          <p style={{ color: '#aaa', marginBottom: '1rem', fontSize: '0.9rem' }}>
            Automatically scan your candidate database, find matching candidates, and submit their profiles to the VMS platform.
          </p>
          <button 
            className="btn btn-primary" 
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', background: 'var(--accent)', border: 'none' }}
            onClick={async (e) => {
              const btn = e.currentTarget;
              const originalText = btn.innerHTML;
              btn.innerHTML = 'Queuing...';
              btn.disabled = true;
              try {
                await axios.post(`${ORCHESTRATOR}/requisitions/${id}/match`);
                btn.innerHTML = 'Auto-Apply Queued!';
                btn.style.background = 'var(--success)';
              } catch (err) {
                alert('Error queuing auto-apply: ' + err.message);
                btn.innerHTML = originalText;
                btn.disabled = false;
              }
            }}
          >
            <MessageSquare size={16} /> Start Auto-Apply Process
          </button>
        </div>

        <div>
          <h3>Source Details</h3>
          <p style={{ color: '#aaa' }}>
            Aggregated from <strong>{job.vms_platform}</strong>.
          </p>
          <pre style={{ whiteSpace: 'pre-wrap', background: '#111', padding: '1rem', borderRadius: '4px', fontSize: '0.85rem' }}>
            {job.description}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default JobDetail;
