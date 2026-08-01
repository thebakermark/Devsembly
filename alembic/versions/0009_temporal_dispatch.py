"""Dispatch committed workflow runs to Temporal.

Revision ID: 0009_temporal_dispatch
Revises: 0008_audit_outbox
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_temporal_dispatch"
down_revision = "0008_audit_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_dispatches",
        sa.Column(
            "workflow_run_id",
            sa.UUID(),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "source_event_id",
            sa.UUID(),
            sa.ForeignKey("published_events.event_id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("temporal_workflow_id", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("claimed_by", sa.String(255)),
        sa.Column("claimed_until", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'dispatched', 'skipped')",
            name="ck_workflow_dispatches_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_workflow_dispatches_attempt_count",
        ),
    )
    op.create_index(
        "ix_workflow_dispatches_claimable",
        "workflow_dispatches",
        ["available_at", "created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_workflow_dispatches_claimed_until",
        "workflow_dispatches",
        ["claimed_until"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_dispatches_claimed_until",
        table_name="workflow_dispatches",
    )
    op.drop_index(
        "ix_workflow_dispatches_claimable",
        table_name="workflow_dispatches",
    )
    op.drop_table("workflow_dispatches")
