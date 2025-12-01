-- Migration: Create video_jobs table for async video rendering
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS video_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slide_id UUID REFERENCES slides(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  video_url TEXT,
  error_message TEXT,
  input_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_video_jobs_slide_id ON video_jobs(slide_id);
CREATE INDEX IF NOT EXISTS idx_video_jobs_user_id ON video_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON video_jobs(status);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_video_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_video_jobs_updated_at ON video_jobs;
CREATE TRIGGER trigger_video_jobs_updated_at
  BEFORE UPDATE ON video_jobs
  FOR EACH ROW
  EXECUTE FUNCTION update_video_jobs_updated_at();

-- RLS policies (allow service role full access)
ALTER TABLE video_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can do all" ON video_jobs
  FOR ALL
  USING (true)
  WITH CHECK (true);
