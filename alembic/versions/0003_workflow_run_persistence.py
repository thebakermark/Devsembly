"""Persist governed workflow runs, steps, and attempts.

Revision ID: 0003_workflow_runs
Revises: 0002_genesis_api
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_workflow_runs"
down_revision = "0002_genesis_api"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("workflow_kind", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "workflow_runs",
        sa.Column(
            "input_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("retry_of_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workflow_runs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE workflow_runs
        SET workflow_kind = COALESCE(workflow_kind, 'legacy'),
            idempotency_key = COALESCE(idempotency_key, 'legacy-' || id::text)
        """
    )
    op.alter_column(
        "workflow_runs",
        "workflow_kind",
        existing_type=sa.String(length=120),
        nullable=False,
    )
    op.alter_column(
        "workflow_runs",
        "idempotency_key",
        existing_type=sa.String(length=200),
        nullable=False,
    )
    op.alter_column(
        "workflow_runs",
        "input_payload",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=None,
    )
    op.drop_constraint(
        "workflow_runs_project_id_fkey",
        "workflow_runs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "workflow_runs_project_id_fkey",
        "workflow_runs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "workflow_runs",
        "project_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "workflow_runs",
        "temporal_workflow_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.create_foreign_key(
        "workflow_runs_retry_of_run_id_fkey",
        "workflow_runs",
        "workflow_runs",
        ["retry_of_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_workflow_runs_status",
        "workflow_runs",
        "status IN ('accepted', 'queued', 'running', 'cancellation_requested', "
        "'succeeded', 'failed', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_workflow_runs_kind",
        "workflow_runs",
        "char_length(btrim(workflow_kind)) > 0",
    )
    op.create_check_constraint(
        "ck_workflow_runs_idempotency_key",
        "workflow_runs",
        "char_length(btrim(idempotency_key)) > 0",
    )
    op.create_check_constraint(
        "ck_workflow_runs_temporal_id",
        "workflow_runs",
        "temporal_workflow_id IS NULL OR char_length(btrim(temporal_workflow_id)) > 0",
    )
    op.create_check_constraint(
        "ck_workflow_runs_cost_estimate",
        "workflow_runs",
        "cost_estimate IS NULL OR cost_estimate >= 0",
    )
    op.create_check_constraint(
        "ck_workflow_runs_version",
        "workflow_runs",
        "version > 0",
    )
    op.create_unique_constraint(
        "uq_workflow_runs_project_idempotency",
        "workflow_runs",
        ["project_id", "idempotency_key"],
    )
    op.create_index(
        "ix_workflow_runs_project_status",
        "workflow_runs",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_workflow_runs_retry_of_run_id",
        "workflow_runs",
        ["retry_of_run_id"],
        unique=False,
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled', 'skipped')",
            name="ck_workflow_steps_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(key)) > 0",
            name="ck_workflow_steps_key",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0",
            name="ck_workflow_steps_name",
        ),
        sa.CheckConstraint("position >= 0", name="ck_workflow_steps_position"),
        sa.CheckConstraint("version > 0", name="ck_workflow_steps_version"),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "key",
            name="uq_workflow_steps_run_key",
        ),
        sa.UniqueConstraint(
            "workflow_run_id",
            "position",
            name="uq_workflow_steps_run_position",
        ),
    )
    op.create_index(
        "ix_workflow_steps_run_status",
        "workflow_steps",
        ["workflow_run_id", "status"],
        unique=False,
    )

    op.create_table(
        "workflow_step_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "result_payload",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column(
            "error_payload",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'cancelled')",
            name="ck_workflow_step_attempts_status",
        ),
        sa.CheckConstraint(
            "attempt_number > 0",
            name="ck_workflow_step_attempts_number",
        ),
        sa.CheckConstraint(
            "(status = 'succeeded' AND result_payload IS NOT NULL "
            "AND error_payload IS NULL) "
            "OR (status = 'failed' AND error_payload IS NOT NULL) "
            "OR status = 'cancelled'",
            name="ck_workflow_step_attempts_payload",
        ),
        sa.CheckConstraint(
            "completed_at >= started_at",
            name="ck_workflow_step_attempts_time_order",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_step_id"],
            ["workflow_steps.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workflow_step_id",
            "attempt_number",
            name="uq_workflow_step_attempts_step_number",
        ),
    )
    op.create_index(
        "ix_workflow_step_attempts_step_id",
        "workflow_step_attempts",
        ["workflow_step_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_step_attempts_step_id",
        table_name="workflow_step_attempts",
    )
    op.drop_table("workflow_step_attempts")
    op.drop_index("ix_workflow_steps_run_status", table_name="workflow_steps")
    op.drop_table("workflow_steps")

    op.drop_index("ix_workflow_runs_retry_of_run_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_project_status", table_name="workflow_runs")
    op.drop_constraint(
        "uq_workflow_runs_project_idempotency",
        "workflow_runs",
        type_="unique",
    )
    op.drop_constraint(
        "ck_workflow_runs_version",
        "workflow_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_workflow_runs_cost_estimate",
        "workflow_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_workflow_runs_temporal_id",
        "workflow_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_workflow_runs_idempotency_key",
        "workflow_runs",
        type_="check",
    )
    op.drop_constraint("ck_workflow_runs_kind", "workflow_runs", type_="check")
    op.drop_constraint("ck_workflow_runs_status", "workflow_runs", type_="check")
    op.drop_constraint(
        "workflow_runs_retry_of_run_id_fkey",
        "workflow_runs",
        type_="foreignkey",
    )
    op.alter_column(
        "workflow_runs",
        "project_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.drop_constraint(
        "workflow_runs_project_id_fkey",
        "workflow_runs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "workflow_runs_project_id_fkey",
        "workflow_runs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE workflow_runs
        SET temporal_workflow_id = 'legacy-' || id::text
        WHERE temporal_workflow_id IS NULL
        """
    )
    op.alter_column(
        "workflow_runs",
        "temporal_workflow_id",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.drop_column("workflow_runs", "completed_at")
    op.drop_column("workflow_runs", "started_at")
    op.drop_column("workflow_runs", "cancellation_requested_at")
    op.drop_column("workflow_runs", "version")
    op.drop_column("workflow_runs", "retry_of_run_id")
    op.drop_column("workflow_runs", "input_payload")
    op.drop_column("workflow_runs", "idempotency_key")
    op.drop_column("workflow_runs", "workflow_kind")
