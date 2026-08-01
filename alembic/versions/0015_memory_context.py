"""Add governed memory and context packages.

Revision ID: 0015_memory_context
Revises: 0014_pie_assurance
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0015_memory_context"
down_revision = "0014_pie_assurance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("sensitivity", sa.String(20), nullable=False),
        sa.Column(
            "source_revision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_state_revisions.id", ondelete="SET NULL"),
        ),
        sa.Column("source_uri", sa.String(1000)),
        sa.Column("assertion_status", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True)),
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_memories.id", ondelete="SET NULL"),
        ),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("proposed_by", sa.String(200), nullable=False),
        sa.Column("decided_by", sa.String(200)),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('working', 'episodic', 'semantic', 'procedural', 'reflection')",
            name="ck_project_memories_kind",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected')", name="ck_project_memories_status"
        ),
        sa.CheckConstraint(
            "sensitivity IN ('public', 'internal', 'confidential', 'restricted')",
            name="ck_project_memories_sensitivity",
        ),
        sa.CheckConstraint(
            "assertion_status IN ('verified', 'inferred', 'disputed')",
            name="ck_project_memories_assertion",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_project_memories_confidence"
        ),
        sa.CheckConstraint("version > 0", name="ck_project_memories_version"),
        sa.UniqueConstraint("project_id", "content_sha256", name="uq_project_memory_content"),
    )
    op.create_index(
        "ix_project_memories_retrieval", "project_memories", ["project_id", "status", "kind"]
    )
    op.create_table(
        "context_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_revision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_state_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("omissions", postgresql.JSONB(), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("token_budget > 0", name="ck_context_packages_budget"),
        sa.CheckConstraint(
            "tokens_used >= 0 AND tokens_used <= token_budget", name="ck_context_packages_usage"
        ),
    )
    op.create_index(
        "ix_context_packages_project_created", "context_packages", ["project_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_context_packages_project_created", table_name="context_packages")
    op.drop_table("context_packages")
    op.drop_index("ix_project_memories_retrieval", table_name="project_memories")
    op.drop_table("project_memories")
