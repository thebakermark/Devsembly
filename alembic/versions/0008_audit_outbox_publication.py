"""Add the audit and transactional-outbox publication backbone.

Revision ID: 0008_audit_outbox
Revises: 0007_evidence_lifecycle
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_audit_outbox"
down_revision = "0007_evidence_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("organization_id", sa.UUID()))
    op.add_column("audit_events", sa.Column("project_id", sa.UUID()))
    op.add_column("audit_events", sa.Column("correlation_id", sa.String(255)))
    op.add_column(
        "audit_events",
        sa.Column("outcome", sa.String(20), server_default="success", nullable=False),
    )
    op.create_check_constraint(
        "ck_audit_events_outcome",
        "audit_events",
        "outcome IN ('success', 'allow', 'deny', 'failure')",
    )
    op.create_index(
        "ix_audit_events_organization_occurred",
        "audit_events",
        ["organization_id", "occurred_at"],
    )
    op.create_index(
        "ix_audit_events_project_occurred",
        "audit_events",
        ["project_id", "occurred_at"],
    )
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])
    op.execute(
        """
        CREATE FUNCTION reject_audit_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_audit_event_mutation()
        """
    )

    op.add_column(
        "outbox_events",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("outbox_events", sa.Column("available_at", sa.DateTime(timezone=True)))
    op.add_column("outbox_events", sa.Column("claimed_by", sa.String(255)))
    op.add_column("outbox_events", sa.Column("claimed_until", sa.DateTime(timezone=True)))
    op.add_column("outbox_events", sa.Column("last_error", sa.Text()))
    op.execute("UPDATE outbox_events SET available_at = occurred_at")
    op.alter_column("outbox_events", "available_at", nullable=False, server_default=sa.func.now())
    op.create_check_constraint(
        "ck_outbox_events_attempt_count", "outbox_events", "attempt_count >= 0"
    )
    op.create_index(
        "ix_outbox_events_publishable",
        "outbox_events",
        ["available_at", "occurred_at"],
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.create_index("ix_outbox_events_claimed_until", "outbox_events", ["claimed_until"])

    op.create_table(
        "published_events",
        sa.Column(
            "event_id",
            sa.UUID(),
            sa.ForeignKey("outbox_events.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("sequence", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("topic", sa.String(120), nullable=False),
        sa.Column("aggregate_id", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_published_events_sequence", "published_events", ["sequence"], unique=True)
    op.create_index(
        "ix_published_events_topic_sequence",
        "published_events",
        ["topic", "sequence"],
    )

    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_name", sa.String(120), primary_key=True),
        sa.Column("worker_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "status IN ('starting', 'ready', 'degraded', 'stopping')",
            name="ck_worker_heartbeats_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("worker_heartbeats")
    op.drop_index("ix_published_events_topic_sequence", table_name="published_events")
    op.drop_index("ix_published_events_sequence", table_name="published_events")
    op.drop_table("published_events")
    op.drop_index("ix_outbox_events_claimed_until", table_name="outbox_events")
    op.drop_index("ix_outbox_events_publishable", table_name="outbox_events")
    op.drop_constraint("ck_outbox_events_attempt_count", "outbox_events", type_="check")
    op.drop_column("outbox_events", "last_error")
    op.drop_column("outbox_events", "claimed_until")
    op.drop_column("outbox_events", "claimed_by")
    op.drop_column("outbox_events", "available_at")
    op.drop_column("outbox_events", "attempt_count")

    op.execute("DROP TRIGGER audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION reject_audit_event_mutation()")
    op.drop_index("ix_audit_events_correlation_id", table_name="audit_events")
    op.drop_index("ix_audit_events_project_occurred", table_name="audit_events")
    op.drop_index("ix_audit_events_organization_occurred", table_name="audit_events")
    op.drop_constraint("ck_audit_events_outcome", "audit_events", type_="check")
    op.drop_column("audit_events", "outcome")
    op.drop_column("audit_events", "correlation_id")
    op.drop_column("audit_events", "project_id")
    op.drop_column("audit_events", "organization_id")
