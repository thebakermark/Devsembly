"""Add durable GitHub ingestion and reconciliation state.

Revision ID: 0012_github_sync
Revises: 0011_pie_projections
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0012_github_sync"
down_revision = "0011_pie_projections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "github_deliveries",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("repository_id", sa.String(80), nullable=False),
        sa.Column("delivery_id", sa.String(100), nullable=False),
        sa.Column("event_name", sa.String(80), nullable=False),
        sa.Column("action", sa.String(80)),
        sa.Column("entity_kind", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(240), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("provider_occurred_at", sa.DateTime(timezone=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("out_of_order", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint(
            "status IN ('received', 'processed', 'failed')", name="ck_github_deliveries_status"
        ),
        sa.UniqueConstraint("repository_id", "delivery_id", name="uq_github_delivery_provider_id"),
    )
    op.create_index(
        "ix_github_deliveries_project_observed", "github_deliveries", ["project_id", "observed_at"]
    )
    op.create_table(
        "github_source_states",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("repository_id", sa.String(80), nullable=False),
        sa.Column("entity_kind", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(240), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("authority", sa.String(20), nullable=False),
        sa.Column("last_delivery_id", sa.String(100), nullable=False),
        sa.Column("provider_occurred_at", sa.DateTime(timezone=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stale_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "reconciliation_required", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.CheckConstraint(
            "authority IN ('inferred', 'verified', 'approved')", name="ck_github_source_authority"
        ),
        sa.UniqueConstraint("project_id", "entity_id", name="uq_github_source_entity"),
    )
    op.create_index(
        "ix_github_source_states_project_stale",
        "github_source_states",
        ["project_id", "stale_after"],
    )
    op.create_table(
        "github_reconciliation_conflicts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.String(240), nullable=False),
        sa.Column("current_sha256", sa.String(64), nullable=False),
        sa.Column("incoming_sha256", sa.String(64), nullable=False),
        sa.Column("current_authority", sa.String(20), nullable=False),
        sa.Column("incoming_authority", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_github_conflicts_status"),
        sa.UniqueConstraint(
            "project_id", "entity_id", "incoming_sha256", name="uq_github_conflict_incoming"
        ),
    )
    op.create_index(
        "ix_github_conflicts_project_status",
        "github_reconciliation_conflicts",
        ["project_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("github_reconciliation_conflicts")
    op.drop_table("github_source_states")
    op.drop_table("github_deliveries")
