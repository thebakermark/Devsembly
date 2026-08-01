"""Add Genesis API persistence invariants.

Revision ID: 0002_genesis_api
Revises: 0001_genesis
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_genesis_api"
down_revision = "0001_genesis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("organizations", "initiatives", "projects", "budgets"):
        op.add_column(
            table_name,
            sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        )

    op.create_check_constraint(
        "ck_organizations_name", "organizations", "char_length(btrim(name)) > 0"
    )
    op.create_check_constraint("ck_organizations_version", "organizations", "version > 0")

    op.create_check_constraint(
        "ck_initiatives_status",
        "initiatives",
        "status IN ('proposed', 'active', 'paused', 'completed', 'cancelled')",
    )
    op.create_check_constraint("ck_initiatives_name", "initiatives", "char_length(btrim(name)) > 0")
    op.create_check_constraint(
        "ck_initiatives_objective",
        "initiatives",
        "char_length(btrim(objective)) > 0",
    )
    op.create_check_constraint("ck_initiatives_version", "initiatives", "version > 0")
    op.create_index(
        "ix_initiatives_organization_id", "initiatives", ["organization_id"], unique=False
    )

    op.create_check_constraint(
        "ck_projects_status",
        "projects",
        "status IN ('planned', 'active', 'blocked', 'completed', 'cancelled')",
    )
    op.create_check_constraint("ck_projects_name", "projects", "char_length(btrim(name)) > 0")
    op.create_check_constraint("ck_projects_version", "projects", "version > 0")
    op.create_index("ix_projects_initiative_id", "projects", ["initiative_id"], unique=False)

    op.create_check_constraint("ck_budgets_monthly_limit_positive", "budgets", "monthly_limit > 0")
    op.create_check_constraint(
        "ck_budgets_currency",
        "budgets",
        "currency ~ '^[A-Z]{3}$'",
    )
    op.create_check_constraint(
        "ck_budgets_enforcement_mode",
        "budgets",
        "enforcement_mode IN ('observe', 'warn', 'block')",
    )
    op.create_check_constraint("ck_budgets_version", "budgets", "version > 0")
    op.create_unique_constraint("uq_budgets_project_id", "budgets", ["project_id"])


def downgrade() -> None:
    op.drop_constraint("uq_budgets_project_id", "budgets", type_="unique")
    op.drop_constraint("ck_budgets_version", "budgets", type_="check")
    op.drop_constraint("ck_budgets_enforcement_mode", "budgets", type_="check")
    op.drop_constraint("ck_budgets_currency", "budgets", type_="check")
    op.drop_constraint("ck_budgets_monthly_limit_positive", "budgets", type_="check")

    op.drop_index("ix_projects_initiative_id", table_name="projects")
    op.drop_constraint("ck_projects_version", "projects", type_="check")
    op.drop_constraint("ck_projects_name", "projects", type_="check")
    op.drop_constraint("ck_projects_status", "projects", type_="check")

    op.drop_index("ix_initiatives_organization_id", table_name="initiatives")
    op.drop_constraint("ck_initiatives_version", "initiatives", type_="check")
    op.drop_constraint("ck_initiatives_objective", "initiatives", type_="check")
    op.drop_constraint("ck_initiatives_name", "initiatives", type_="check")
    op.drop_constraint("ck_initiatives_status", "initiatives", type_="check")

    op.drop_constraint("ck_organizations_version", "organizations", type_="check")
    op.drop_constraint("ck_organizations_name", "organizations", type_="check")

    for table_name in ("budgets", "projects", "initiatives", "organizations"):
        op.drop_column(table_name, "version")
