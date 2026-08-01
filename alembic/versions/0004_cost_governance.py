"""Add cost evaluations and governed decision records.

Revision ID: 0004_cost_governance
Revises: 0003_workflow_runs
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004_cost_governance"
down_revision = "0003_workflow_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("budget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("budget_monthly_limit", sa.Numeric(14, 4), nullable=False),
        sa.Column("budget_version", sa.Integer(), nullable=False),
        sa.Column("enforcement_mode", sa.String(length=20), nullable=False),
        sa.Column(
            "selected_option",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "alternatives",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("selected_one_time_cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("selected_monthly_cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("monthly_overage", sa.Numeric(14, 4), nullable=False),
        sa.Column(
            "recommendation",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column("algorithm_version", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(btrim(idempotency_key)) > 0",
            name="ck_cost_evaluations_idempotency_key",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_cost_evaluations_request_fingerprint",
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_cost_evaluations_currency",
        ),
        sa.CheckConstraint(
            "budget_monthly_limit > 0",
            name="ck_cost_evaluations_budget_limit",
        ),
        sa.CheckConstraint(
            "budget_version > 0",
            name="ck_cost_evaluations_budget_version",
        ),
        sa.CheckConstraint(
            "enforcement_mode IN ('observe', 'warn', 'block')",
            name="ck_cost_evaluations_enforcement_mode",
        ),
        sa.CheckConstraint(
            "outcome IN ('within_budget', 'observed_overage', 'approval_required', 'blocked')",
            name="ck_cost_evaluations_outcome",
        ),
        sa.CheckConstraint(
            "selected_one_time_cost >= 0 AND selected_monthly_cost >= 0",
            name="ck_cost_evaluations_selected_costs",
        ),
        sa.CheckConstraint(
            "monthly_overage >= 0",
            name="ck_cost_evaluations_monthly_overage",
        ),
        sa.CheckConstraint(
            "monthly_overage = GREATEST(selected_monthly_cost - budget_monthly_limit, 0)",
            name="ck_cost_evaluations_overage_math",
        ),
        sa.CheckConstraint(
            "(outcome = 'within_budget' AND selected_monthly_cost <= budget_monthly_limit) "
            "OR (outcome = 'observed_overage' AND enforcement_mode = 'observe' "
            "AND selected_monthly_cost > budget_monthly_limit) "
            "OR (outcome = 'approval_required' AND enforcement_mode = 'warn' "
            "AND selected_monthly_cost > budget_monthly_limit) "
            "OR (outcome = 'blocked' AND enforcement_mode = 'block' "
            "AND selected_monthly_cost > budget_monthly_limit)",
            name="ck_cost_evaluations_outcome_math",
        ),
        sa.CheckConstraint(
            "char_length(btrim(algorithm_version)) > 0",
            name="ck_cost_evaluations_algorithm_version",
        ),
        sa.ForeignKeyConstraint(
            ["budget_id"],
            ["budgets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_cost_evaluations_project_idempotency",
        ),
    )
    op.create_index(
        "ix_cost_evaluations_project_created",
        "cost_evaluations",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cost_evaluations_budget_id",
        "cost_evaluations",
        ["budget_id"],
        unique=False,
    )
    op.create_index(
        "ix_cost_evaluations_workflow_run_id",
        "cost_evaluations",
        ["workflow_run_id"],
        unique=False,
    )

    op.add_column(
        "decisions",
        sa.Column("cost_evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'USD'"),
            nullable=False,
        ),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "estimated_one_time_cost",
            sa.Numeric(14, 4),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.alter_column(
        "decisions",
        "estimated_monthly_cost",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(14, 4),
        existing_nullable=False,
    )
    op.add_column(
        "decisions",
        sa.Column(
            "risk",
            sa.String(length=20),
            server_default=sa.text("'moderate'"),
            nullable=False,
        ),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "confidence",
            sa.Numeric(5, 4),
            server_default=sa.text("0.5"),
            nullable=False,
        ),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "rationale",
            sa.Text(),
            server_default=sa.text("'Legacy decision record'"),
            nullable=False,
        ),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'proposed'"),
            nullable=False,
        ),
    )
    op.add_column("decisions", sa.Column("decided_by", sa.String(length=255)))
    op.add_column("decisions", sa.Column("decision_note", sa.Text()))
    op.add_column("decisions", sa.Column("outcome", sa.Text()))
    op.add_column(
        "decisions",
        sa.Column("authorization_budget_version", sa.Integer()),
    )
    op.add_column(
        "decisions",
        sa.Column("authorization_monthly_limit", sa.Numeric(14, 4)),
    )
    op.add_column(
        "decisions",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "decisions",
        sa.Column("decided_at", sa.DateTime(timezone=True)),
    )
    op.alter_column(
        "decisions",
        "currency",
        existing_type=sa.String(length=3),
        server_default=None,
    )
    op.alter_column(
        "decisions",
        "estimated_one_time_cost",
        existing_type=sa.Numeric(14, 4),
        server_default=None,
    )
    op.alter_column(
        "decisions",
        "risk",
        existing_type=sa.String(length=20),
        server_default=None,
    )
    op.alter_column(
        "decisions",
        "confidence",
        existing_type=sa.Numeric(5, 4),
        server_default=None,
    )
    op.alter_column(
        "decisions",
        "rationale",
        existing_type=sa.Text(),
        server_default=None,
    )
    op.alter_column(
        "decisions",
        "status",
        existing_type=sa.String(length=20),
        server_default=None,
    )
    op.create_foreign_key(
        "decisions_cost_evaluation_id_fkey",
        "decisions",
        "cost_evaluations",
        ["cost_evaluation_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_decisions_title",
        "decisions",
        "char_length(btrim(title)) > 0",
    )
    op.create_check_constraint(
        "ck_decisions_context",
        "decisions",
        "char_length(btrim(context)) > 0",
    )
    op.create_check_constraint(
        "ck_decisions_selected_option",
        "decisions",
        "char_length(btrim(selected_option)) > 0",
    )
    op.create_check_constraint(
        "ck_decisions_currency",
        "decisions",
        "currency ~ '^[A-Z]{3}$'",
    )
    op.create_check_constraint(
        "ck_decisions_estimated_costs",
        "decisions",
        "estimated_one_time_cost >= 0 AND estimated_monthly_cost >= 0",
    )
    op.create_check_constraint(
        "ck_decisions_risk",
        "decisions",
        "risk IN ('low', 'moderate', 'high', 'critical')",
    )
    op.create_check_constraint(
        "ck_decisions_confidence",
        "decisions",
        "confidence >= 0 AND confidence <= 1",
    )
    op.create_check_constraint(
        "ck_decisions_rationale",
        "decisions",
        "char_length(btrim(rationale)) > 0",
    )
    op.create_check_constraint(
        "ck_decisions_status",
        "decisions",
        "status IN ('proposed', 'approved', 'rejected')",
    )
    op.create_check_constraint(
        "ck_decisions_lifecycle",
        "decisions",
        "(status = 'proposed' AND decided_by IS NULL AND decision_note IS NULL "
        "AND outcome IS NULL AND decided_at IS NULL "
        "AND authorization_budget_version IS NULL "
        "AND authorization_monthly_limit IS NULL) OR "
        "(status IN ('approved', 'rejected') "
        "AND char_length(btrim(decided_by)) > 0 "
        "AND char_length(btrim(decision_note)) > 0 "
        "AND char_length(btrim(outcome)) > 0 AND decided_at IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_decisions_authorization_budget_version",
        "decisions",
        "authorization_budget_version IS NULL OR authorization_budget_version > 0",
    )
    op.create_check_constraint(
        "ck_decisions_authorization_monthly_limit",
        "decisions",
        "authorization_monthly_limit IS NULL OR authorization_monthly_limit > 0",
    )
    op.create_check_constraint(
        "ck_decisions_version",
        "decisions",
        "version > 0",
    )
    op.create_index(
        "ix_decisions_project_status",
        "decisions",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_decisions_cost_evaluation_id",
        "decisions",
        ["cost_evaluation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_decisions_cost_evaluation_id", table_name="decisions")
    op.drop_index("ix_decisions_project_status", table_name="decisions")
    op.drop_constraint("ck_decisions_version", "decisions", type_="check")
    op.drop_constraint(
        "ck_decisions_authorization_monthly_limit",
        "decisions",
        type_="check",
    )
    op.drop_constraint(
        "ck_decisions_authorization_budget_version",
        "decisions",
        type_="check",
    )
    op.drop_constraint("ck_decisions_lifecycle", "decisions", type_="check")
    op.drop_constraint("ck_decisions_status", "decisions", type_="check")
    op.drop_constraint("ck_decisions_rationale", "decisions", type_="check")
    op.drop_constraint("ck_decisions_confidence", "decisions", type_="check")
    op.drop_constraint("ck_decisions_risk", "decisions", type_="check")
    op.drop_constraint("ck_decisions_estimated_costs", "decisions", type_="check")
    op.drop_constraint("ck_decisions_currency", "decisions", type_="check")
    op.drop_constraint("ck_decisions_selected_option", "decisions", type_="check")
    op.drop_constraint("ck_decisions_context", "decisions", type_="check")
    op.drop_constraint("ck_decisions_title", "decisions", type_="check")
    op.drop_constraint(
        "decisions_cost_evaluation_id_fkey",
        "decisions",
        type_="foreignkey",
    )
    op.drop_column("decisions", "decided_at")
    op.drop_column("decisions", "version")
    op.drop_column("decisions", "authorization_monthly_limit")
    op.drop_column("decisions", "authorization_budget_version")
    op.drop_column("decisions", "outcome")
    op.drop_column("decisions", "decision_note")
    op.drop_column("decisions", "decided_by")
    op.drop_column("decisions", "status")
    op.drop_column("decisions", "rationale")
    op.drop_column("decisions", "confidence")
    op.drop_column("decisions", "risk")
    op.alter_column(
        "decisions",
        "estimated_monthly_cost",
        existing_type=sa.Numeric(14, 4),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
    )
    op.drop_column("decisions", "estimated_one_time_cost")
    op.drop_column("decisions", "currency")
    op.drop_column("decisions", "cost_evaluation_id")

    op.drop_index(
        "ix_cost_evaluations_workflow_run_id",
        table_name="cost_evaluations",
    )
    op.drop_index("ix_cost_evaluations_budget_id", table_name="cost_evaluations")
    op.drop_index(
        "ix_cost_evaluations_project_created",
        table_name="cost_evaluations",
    )
    op.drop_table("cost_evaluations")
