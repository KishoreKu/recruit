-- PostgreSQL Schema for VMS Portal

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Jobs table for structured data
CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title VARCHAR(255) NOT NULL,
  company VARCHAR(255),
  skills TEXT[],
  location VARCHAR(255),
  job_type VARCHAR(100),
  salary VARCHAR(100),
  contact TEXT,
  source_platform VARCHAR(100),
  source_group VARCHAR(255),
  raw_text TEXT,
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Users (Recruiting Firms) table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(255),
  email VARCHAR(255) UNIQUE NOT NULL,
  company VARCHAR(255),
  plan VARCHAR(50) DEFAULT 'basic',
  stripe_customer_id VARCHAR(255),
  subscription_status VARCHAR(50) DEFAULT 'inactive',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Saved Jobs (Bookmarks)
CREATE TABLE IF NOT EXISTS saved_jobs (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, job_id)
);

-- Raw Messages log (PostgreSQL version for sync/tracking)
CREATE TABLE IF NOT EXISTS raw_messages_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mongo_id VARCHAR(255), -- Reference to the MongoDB message
  platform VARCHAR(100),
  group_name VARCHAR(255),
  is_processed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
