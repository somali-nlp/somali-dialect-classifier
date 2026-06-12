"""Add run_purpose and campaign_id provenance columns to pipeline_runs

Revision ID: 003
Revises: 002
Create Date: 2026-06-12

Adds two columns that enable campaign lifecycle tracking and run provenance:
  run_purpose TEXT NOT NULL DEFAULT 'production'
    Valid values: production | validation | test
  campaign_id TEXT NULL
    FK-like reference to campaigns.campaign_id; NULL for non-production runs.

The DEFAULT ensures existing rows (e.g. the five COMPLETED production rows from
2026-05-29) are back-filled as 'production' automatically by PostgreSQL.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add run_purpose and campaign_id to pipeline_runs."""
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "run_purpose",
            sa.Text(),
            nullable=False,
            server_default="production",
        ),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "campaign_id",
            sa.Text(),
            nullable=True,
        ),
    )

    # Index to enable efficient filtering by run_purpose
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run_purpose "
        "ON pipeline_runs(run_purpose)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_campaign_id "
        "ON pipeline_runs(campaign_id)"
    )

    op.execute("INSERT INTO schema_version (version) VALUES (3) ON CONFLICT DO NOTHING")


def downgrade() -> None:
    """Remove run_purpose and campaign_id from pipeline_runs."""
    op.execute("DROP INDEX IF EXISTS idx_pipeline_runs_run_purpose")
    op.execute("DROP INDEX IF EXISTS idx_pipeline_runs_campaign_id")
    op.drop_column("pipeline_runs", "campaign_id")
    op.drop_column("pipeline_runs", "run_purpose")
    op.execute("DELETE FROM schema_version WHERE version = 3")
