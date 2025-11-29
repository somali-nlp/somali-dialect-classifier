"""Add pipeline runs tracking table

Revision ID: 002
Revises: 001
Create Date: 2025-11-15

Tracks each pipeline execution for accurate scheduling and monitoring.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create pipeline_runs table."""

    op.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id VARCHAR(255) PRIMARY KEY,
            source VARCHAR(100) NOT NULL,
            pipeline_type VARCHAR(50) NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            status VARCHAR(20) NOT NULL,
            records_discovered INTEGER DEFAULT 0,
            records_processed INTEGER DEFAULT 0,
            records_failed INTEGER DEFAULT 0,
            errors TEXT,
            metrics_path VARCHAR(500),
            config_snapshot TEXT,
            git_commit VARCHAR(40),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes for common queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_source ON pipeline_runs(source)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_start_time ON pipeline_runs(start_time)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_end_time ON pipeline_runs(end_time)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_source_status ON pipeline_runs(source, status)")

    # Update schema version
    op.execute("INSERT INTO schema_version (version) VALUES (2) ON CONFLICT DO NOTHING")


def downgrade() -> None:
    """Drop pipeline_runs table."""
    op.execute("DROP TABLE IF EXISTS pipeline_runs CASCADE")
    op.execute("DELETE FROM schema_version WHERE version = 2")
