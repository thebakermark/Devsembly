"""Add immutable Project Intelligence state revisions.

Revision ID: 0010_project_intelligence
Revises: 0009_temporal_dispatch
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_project_intelligence"
down_revision = "0009_temporal_dispatch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_state_revisions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "parent_revision_id",
            sa.UUID(),
            sa.ForeignKey("project_state_revisions.id", ondelete="RESTRICT"),
        ),
        sa.Column("schema_version", sa.String(40), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False),
        sa.Column("state_sha256", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("source_provider", sa.String(80), nullable=False),
        sa.Column("source_kind", sa.String(80), nullable=False),
        sa.Column("source_event_id", sa.String(255)),
        sa.Column("source_uri", sa.String(1000)),
        sa.Column("source_occurred_at", sa.DateTime(timezone=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assertion_status", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence_explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("version > 0", name="ck_project_state_revisions_version"),
        sa.CheckConstraint(
            "assertion_status IN ('verified', 'inferred', 'disputed')",
            name="ck_project_state_revisions_assertion_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_project_state_revisions_confidence",
        ),
        sa.CheckConstraint(
            "state_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_project_state_revisions_state_sha256",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_project_state_revisions_request_fingerprint",
        ),
        sa.UniqueConstraint(
            "project_id", "version", name="uq_project_state_project_version"
        ),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_project_state_project_idempotency",
        ),
    )
    op.create_index(
        "ix_project_state_project_created",
        "project_state_revisions",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_project_state_source_event",
        "project_state_revisions",
        ["project_id", "source_provider", "source_event_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_state_source_event", table_name="project_state_revisions")
    op.drop_index("ix_project_state_project_created", table_name="project_state_revisions")
    op.drop_table("project_state_revisions")
