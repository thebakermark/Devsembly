"""Add governed GitHub conflict resolution evidence.

Revision ID: 0013_github_conflict_resolution
Revises: 0012_github_sync
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0013_github_conflict_resolution"
down_revision = "0012_github_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("github_reconciliation_conflicts", sa.Column("resolution", sa.String(30)))
    op.add_column("github_reconciliation_conflicts", sa.Column("resolution_reason", sa.Text()))
    op.add_column(
        "github_reconciliation_conflicts",
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True)),
    )
    op.create_foreign_key(
        "fk_github_conflicts_resolved_by",
        "github_reconciliation_conflicts",
        "principals",
        ["resolved_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_github_conflicts_resolved_by", "github_reconciliation_conflicts", type_="foreignkey"
    )
    op.drop_column("github_reconciliation_conflicts", "resolved_by")
    op.drop_column("github_reconciliation_conflicts", "resolution_reason")
    op.drop_column("github_reconciliation_conflicts", "resolution")
