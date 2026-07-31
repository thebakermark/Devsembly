"""Add PIE assurance projection caches.

Revision ID: 0014_pie_assurance
Revises: 0013_github_conflict_resolution
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0014_pie_assurance"
down_revision = "0013_github_conflict_resolution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    empty = sa.text("'[]'::jsonb")
    for name in ("validation_results", "risks", "technical_debt"):
        op.add_column(
            "project_intelligence_projections",
            sa.Column(name, postgresql.JSONB(), nullable=False, server_default=empty),
        )
        op.alter_column("project_intelligence_projections", name, server_default=None)


def downgrade() -> None:
    for name in reversed(("validation_results", "risks", "technical_debt")):
        op.drop_column("project_intelligence_projections", name)
