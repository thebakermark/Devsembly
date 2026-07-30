"""Add immutable evidence metadata.

Revision ID: 0006_evidence
Revises: 0005_identity_authorization
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0006_evidence"
down_revision = "0005_identity_authorization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True)),
        sa.Column("workflow_step_attempt_id", postgresql.UUID(as_uuid=True)),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("content_type", sa.String(200), nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["workflow_step_attempt_id"], ["workflow_step_attempts.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "kind IN ('validation', 'source_control', 'workflow', 'other')", name="ck_evidence_kind"
        ),
        sa.CheckConstraint("char_length(btrim(name)) > 0", name="ck_evidence_name"),
        sa.CheckConstraint("char_length(btrim(content_type)) > 0", name="ck_evidence_content_type"),
        sa.CheckConstraint(
            "object_key ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'", name="ck_evidence_object_key"
        ),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_evidence_sha256"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_evidence_size_bytes"),
        sa.UniqueConstraint("project_id", "object_key", name="uq_evidence_project_object_key"),
    )
    op.create_index("ix_evidence_project_created", "evidence", ["project_id", "created_at"])
    op.create_index("ix_evidence_workflow_run_id", "evidence", ["workflow_run_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_workflow_run_id", table_name="evidence")
    op.drop_index("ix_evidence_project_created", table_name="evidence")
    op.drop_table("evidence")
