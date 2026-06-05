const { pool } = require('../config/db');
const RawMessage = require('../models/RawMessage');
const { parseJobMessage } = require('../services/aiParser');

/**
 * Get list of structured jobs with optional filtering.
 */
const getJobs = async (req, res) => {
  const { skill, location, job_type, source } = req.query;
  
  let query = 'SELECT * FROM jobs WHERE status = $1';
  let values = ['approved'];
  let count = 2;

  if (skill) {
    query += ` AND $${count} = ANY(skills)`;
    values.push(skill);
    count++;
  }
  if (location) {
    query += ` AND location ILIKE $${count}`;
    values.push(`%${location}%`);
    count++;
  }
  if (job_type) {
    query += ` AND job_type = $${count}`;
    values.push(job_type);
    count++;
  }
  if (source) {
    query += ` AND source_platform = $${count}`;
    values.push(source);
    count++;
  }

  query += ' ORDER BY created_at DESC';

  try {
    const { rows } = await pool.query(query, values);
    res.json(rows);
  } catch (err) {
    console.error('Error fetching jobs:', err);
    res.status(500).json({ error: 'Failed to fetch jobs' });
  }
};

/**
 * Get details for a specific job.
 */
const getJobById = async (req, res) => {
  const { id } = req.params;
  try {
    const { rows } = await pool.query('SELECT * FROM jobs WHERE id = $1', [id]);
    if (rows.length === 0) return res.status(404).json({ error: 'Job not found' });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch job detail' });
  }
};

/**
 * Manually trigger AI parsing for a raw message and save to PostgreSQL.
 * (This is typically an admin function)
 */
const processRawJob = async (rawMessageId) => {
  try {
    const rawMsg = await RawMessage.findById(rawMessageId);
    if (!rawMsg) throw new Error('Raw message not found');

    const structuredData = await parseJobMessage(rawMsg.message_text);
    if (!structuredData) throw new Error('AI Parsing failed');

    const { job_title, company, skills, location, job_type, salary, contact } = structuredData;

    const query = `
      INSERT INTO jobs (title, company, skills, location, job_type, salary, contact, source_platform, source_group, raw_text, status)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
      RETURNING *;
    `;
    const values = [
      job_title, company, skills, location, job_type, salary, contact, 
      rawMsg.platform, rawMsg.group_name, rawMsg.message_text, 'pending'
    ];

    const { rows } = await pool.query(query, values);
    
    // Update raw message status
    rawMsg.is_processed = true;
    await rawMsg.save();

    return rows[0];
  } catch (err) {
    console.error('Error processing raw job:', err);
    throw err;
  }
};

module.exports = { getJobs, getJobById, processRawJob };
