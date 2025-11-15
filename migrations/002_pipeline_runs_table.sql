-- Pipeline Runs Tracking Table
-- Tracks each pipeline execution for accurate scheduling and monitoring
-- Migration 002
-- Date: 2025-11-15

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id VARCHAR(255) PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    pipeline_type VARCHAR(50) NOT NULL, -- 'web', 'file', 'stream'
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- 'STARTED', 'RUNNING', 'COMPLETED', 'FAILED'
    records_discovered INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    errors TEXT,
    metrics_path VARCHAR(500),
    config_snapshot TEXT, -- JSON of config used
    git_commit VARCHAR(40), -- Git hash at run time
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_source ON pipeline_runs(source);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_start_time ON pipeline_runs(start_time);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_end_time ON pipeline_runs(end_time);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_source_status ON pipeline_runs(source, status);

-- Insert migration version
INSERT INTO schema_version (version) VALUES (2)
ON CONFLICT DO NOTHING;
