"""Add evidence retention lifecycle metadata.

Revision ID: 0007_evidence_lifecycle
Revises: 0006_evidence
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_evidence_lifecycle"
down_revision = "0006_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("retention_class", sa.String(30), nullable=True))
    op.add_column("evidence", sa.Column("retain_until", sa.DateTime(timezone=True)))
    op.execute(
        "UPDATE evidence SET retention_class = 'standard', "
        "retain_until = created_at + interval '365 days'"
    )
    op.alter_column("evidence", "retention_class", nullable=False)
    op.create_check_constraint(
        "ck_evidence_retention_class",
        "evidence",
        "retention_class IN ('transient', 'standard', 'compliance', 'permanent')",
    )
    op.create_check_constraint(
        "ck_evidence_retention_deadline",
        "evidence",
        "(retention_class = 'permanent' AND retain_until IS NULL) "
        "OR (retention_class <> 'permanent' AND retain_until IS NOT NULL "
        "AND retain_until > created_at)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_evidence_retention_deadline", "evidence", type_="check")
    op.drop_constraint("ck_evidence_retention_class", "evidence", type_="check")
    op.drop_column("evidence", "retain_until")
    op.drop_column("evidence", "retention_class")
