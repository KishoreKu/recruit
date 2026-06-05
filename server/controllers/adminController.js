const RawMessage = require('../models/RawMessage');
const { pool } = require('../config/db');
const { processRawJob } = require('./jobController');

/**
 * Get all raw messages for review.
 */
const getRawMessages = async (req, res) => {
  try {
    const messages = await RawMessage.find().sort({ created_at: -1 });
    res.json(messages);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch raw messages' });
  }
};

/**
 * Trigger AI parsing and approve a raw message.
 */
const approveRawMessage = async (req, res) => {
  const { id } = req.params; // MongoDB ID
  try {
    const job = await processRawJob(id);
    res.json({ message: 'Job parsed and pending approval', job });
  } catch (err) {
    res.status(500).json({ error: err.message || 'Failed to approve raw message' });
  }
};

/**
 * Final approval of a parsed job to make it public.
 */
const finalizeJob = async (req, res) => {
  const { id } = req.params; // Postgres UUID
  try {
    const query = 'UPDATE jobs SET status = $1 WHERE id = $2 RETURNING *';
    const { rows } = await pool.query(query, ['approved', id]);
    if (rows.length === 0) return res.status(404).json({ error: 'Job not found' });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: 'Failed to finalize job' });
  }
};

module.exports = { getRawMessages, approveRawMessage, finalizeJob };
