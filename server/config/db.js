const mongoose = require('mongoose');
const { Pool } = require('pg');
require('dotenv').config();

// MongoDB Connection
const connectMongo = async () => {
  try {
    await mongoose.connect(process.env.MONGO_URI || 'mongodb://localhost:27017/vms_raw_messages');
    console.log('Connected to MongoDB (Raw Messages)');
  } catch (err) {
    console.error('MongoDB Connection Error:', err);
    process.exit(1);
  }
};

// PostgreSQL Connection
const pool = new Pool({
  host: process.env.PG_HOST || 'localhost',
  port: process.env.PG_PORT || 5432,
  user: process.env.PG_USER || 'postgres',
  password: process.env.PG_PASSWORD || '',
  database: process.env.PG_DATABASE || 'vms_jobs'
});

const connectPostgres = async () => {
  try {
    await pool.connect();
    console.log('Connected to PostgreSQL (Structured Data)');
  } catch (err) {
    console.error('PostgreSQL Connection Error:', err);
    process.exit(1);
  }
};

module.exports = { connectMongo, connectPostgres, pool };
