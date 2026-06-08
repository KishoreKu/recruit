import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Building, DollarSign, Calendar, MessageSquare } from 'lucide-react';

const JobDetail = () => {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJob = async () => {
      try {
        const res = await axios.get(`/api/jobs/${id}`);
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
            <Building size={18} style={{ marginRight: '8px' }} /> <strong>Company:</strong>&nbsp;{job.company || 'Not Specified'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <MapPin size={18} style={{ marginRight: '8px' }} /> <strong>Location:</strong>&nbsp;{job.location || 'Remote'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <DollarSign size={18} style={{ marginRight: '8px' }} /> <strong>Salary:</strong>&nbsp;{job.salary || 'Competitive'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Calendar size={18} style={{ marginRight: '8px' }} /> <strong>Posted:</strong>&nbsp;{new Date(job.created_at).toLocaleDateString()}
          </div>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h3>Required Skills</h3>
          <div className="job-skills">
            {job.skills && job.skills.map((skill, index) => (
              <span key={index} className="skill-tag" style={{ fontSize: '1rem', padding: '4px 12px' }}>{skill}</span>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h3>Contact / How to Apply</h3>
          <p style={{ background: '#222', padding: '1rem', borderRadius: '4px' }}>
            {job.contact || 'Please refer to the source.'}
          </p>
        </div>

        <div>
          <h3>Source Details</h3>
          <p style={{ color: '#aaa' }}>
            Aggregated from <strong>{job.source_platform}</strong> group <em>{job.source_group}</em>.
          </p>
          <pre style={{ whiteSpace: 'pre-wrap', background: '#111', padding: '1rem', borderRadius: '4px', fontSize: '0.85rem' }}>
            {job.raw_text}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default JobDetail;
