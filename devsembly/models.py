from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from devsembly.database import Base


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Organization(Timestamped, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("char_length(btrim(name)) > 0", name="ck_organizations_name"),
        CheckConstraint("version > 0", name="ck_organizations_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )


class Principal(Timestamped, Base):
    __tablename__ = "principals"
    __table_args__ = (
        CheckConstraint("kind = 'human'", name="ck_principals_kind"),
        CheckConstraint("char_length(btrim(display_name)) > 0", name="ck_principals_display_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(
        String(20), default="human", server_default=text("'human'"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)


class ExternalIdentity(Timestamped, Base):
    __tablename__ = "external_identities"
    __table_args__ = (
        CheckConstraint("char_length(btrim(issuer)) > 0", name="ck_external_identities_issuer"),
        CheckConstraint("char_length(btrim(subject)) > 0", name="ck_external_identities_subject"),
        UniqueConstraint("issuer", "subject", name="uq_external_identities_issuer_subject"),
        Index("ix_external_identities_principal_id", "principal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    principal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("principals.id", ondelete="CASCADE"), nullable=False
    )
    issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)


class OrganizationMembership(Timestamped, Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'administrator', 'operator', 'approver', 'viewer')",
            name="ck_organization_memberships_role",
        ),
        CheckConstraint(
            "status IN ('active', 'suspended', 'revoked')",
            name="ck_organization_memberships_status",
        ),
        UniqueConstraint(
            "organization_id", "principal_id", name="uq_organization_memberships_org_principal"
        ),
        Index("ix_organization_memberships_principal_status", "principal_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    principal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("principals.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default=text("'active'"), nullable=False
    )


class AuthorizationDelegation(Timestamped, Base):
    __tablename__ = "authorization_delegations"
    __table_args__ = (
        CheckConstraint("char_length(btrim(action)) > 0", name="ck_delegations_action"),
        CheckConstraint("expires_at > starts_at", name="ck_delegations_time_order"),
        Index("ix_delegations_recipient_active", "recipient_principal_id", "revoked_at"),
        Index("ix_delegations_organization_id", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    grantor_principal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("principals.id", ondelete="RESTRICT"), nullable=False
    )
    recipient_principal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("principals.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Initiative(Timestamped, Base):
    __tablename__ = "initiatives"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'active', 'paused', 'completed', 'cancelled')",
            name="ck_initiatives_status",
        ),
        CheckConstraint("char_length(btrim(name)) > 0", name="ck_initiatives_name"),
        CheckConstraint("char_length(btrim(objective)) > 0", name="ck_initiatives_objective"),
        CheckConstraint("version > 0", name="ck_initiatives_version"),
        Index("ix_initiatives_organization_id", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="proposed", nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )


class Project(Timestamped, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'active', 'blocked', 'completed', 'cancelled')",
            name="ck_projects_status",
        ),
        CheckConstraint("char_length(btrim(name)) > 0", name="ck_projects_name"),
        CheckConstraint("version > 0", name="ck_projects_version"),
        Index("ix_projects_initiative_id", "initiative_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    initiative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    repository: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), default="planned", nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )


class Budget(Timestamped, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("monthly_limit > 0", name="ck_budgets_monthly_limit_positive"),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_budgets_currency",
        ),
        CheckConstraint(
            "enforcement_mode IN ('observe', 'warn', 'block')",
            name="ck_budgets_enforcement_mode",
        ),
        CheckConstraint("version > 0", name="ck_budgets_version"),
        UniqueConstraint("project_id", name="uq_budgets_project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    enforcement_mode: Mapped[str] = mapped_column(String(20), default="warn", nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )


class CostEvaluation(Base):
    __tablename__ = "cost_evaluations"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(idempotency_key)) > 0",
            name="ck_cost_evaluations_idempotency_key",
        ),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_cost_evaluations_request_fingerprint",
        ),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_cost_evaluations_currency",
        ),
        CheckConstraint(
            "budget_monthly_limit > 0",
            name="ck_cost_evaluations_budget_limit",
        ),
        CheckConstraint(
            "budget_version > 0",
            name="ck_cost_evaluations_budget_version",
        ),
        CheckConstraint(
            "enforcement_mode IN ('observe', 'warn', 'block')",
            name="ck_cost_evaluations_enforcement_mode",
        ),
        CheckConstraint(
            "outcome IN ('within_budget', 'observed_overage', 'approval_required', 'blocked')",
            name="ck_cost_evaluations_outcome",
        ),
        CheckConstraint(
            "selected_one_time_cost >= 0 AND selected_monthly_cost >= 0",
            name="ck_cost_evaluations_selected_costs",
        ),
        CheckConstraint(
            "monthly_overage >= 0",
            name="ck_cost_evaluations_monthly_overage",
        ),
        CheckConstraint(
            "monthly_overage = GREATEST(selected_monthly_cost - budget_monthly_limit, 0)",
            name="ck_cost_evaluations_overage_math",
        ),
        CheckConstraint(
            "(outcome = 'within_budget' AND selected_monthly_cost <= budget_monthly_limit) "
            "OR (outcome = 'observed_overage' AND enforcement_mode = 'observe' "
            "AND selected_monthly_cost > budget_monthly_limit) "
            "OR (outcome = 'approval_required' AND enforcement_mode = 'warn' "
            "AND selected_monthly_cost > budget_monthly_limit) "
            "OR (outcome = 'blocked' AND enforcement_mode = 'block' "
            "AND selected_monthly_cost > budget_monthly_limit)",
            name="ck_cost_evaluations_outcome_math",
        ),
        CheckConstraint(
            "char_length(btrim(algorithm_version)) > 0",
            name="ck_cost_evaluations_algorithm_version",
        ),
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_cost_evaluations_project_idempotency",
        ),
        Index("ix_cost_evaluations_project_created", "project_id", "created_at"),
        Index("ix_cost_evaluations_budget_id", "budget_id"),
        Index("ix_cost_evaluations_workflow_run_id", "workflow_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="RESTRICT"), nullable=False
    )
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL")
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    budget_monthly_limit: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    budget_version: Mapped[int] = mapped_column(Integer, nullable=False)
    enforcement_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    selected_option: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    alternatives: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    selected_one_time_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    selected_monthly_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    monthly_overage: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    recommendation: Mapped[dict[str, object] | None] = mapped_column(JSONB(none_as_null=True))
    algorithm_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Decision(Timestamped, Base):
    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint("char_length(btrim(title)) > 0", name="ck_decisions_title"),
        CheckConstraint("char_length(btrim(context)) > 0", name="ck_decisions_context"),
        CheckConstraint(
            "char_length(btrim(selected_option)) > 0",
            name="ck_decisions_selected_option",
        ),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_decisions_currency"),
        CheckConstraint(
            "estimated_one_time_cost >= 0 AND estimated_monthly_cost >= 0",
            name="ck_decisions_estimated_costs",
        ),
        CheckConstraint(
            "risk IN ('low', 'moderate', 'high', 'critical')",
            name="ck_decisions_risk",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_decisions_confidence",
        ),
        CheckConstraint("char_length(btrim(rationale)) > 0", name="ck_decisions_rationale"),
        CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected')",
            name="ck_decisions_status",
        ),
        CheckConstraint(
            "(status = 'proposed' AND decided_by IS NULL AND decision_note IS NULL "
            "AND outcome IS NULL AND decided_at IS NULL "
            "AND authorization_budget_version IS NULL "
            "AND authorization_monthly_limit IS NULL) OR "
            "(status IN ('approved', 'rejected') "
            "AND char_length(btrim(decided_by)) > 0 "
            "AND char_length(btrim(decision_note)) > 0 "
            "AND char_length(btrim(outcome)) > 0 AND decided_at IS NOT NULL)",
            name="ck_decisions_lifecycle",
        ),
        CheckConstraint(
            "authorization_budget_version IS NULL OR authorization_budget_version > 0",
            name="ck_decisions_authorization_budget_version",
        ),
        CheckConstraint(
            "authorization_monthly_limit IS NULL OR authorization_monthly_limit > 0",
            name="ck_decisions_authorization_monthly_limit",
        ),
        CheckConstraint("version > 0", name="ck_decisions_version"),
        Index("ix_decisions_project_status", "project_id", "status"),
        Index("ix_decisions_cost_evaluation_id", "cost_evaluation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    cost_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_evaluations.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    selected_option: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    estimated_one_time_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    estimated_monthly_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    alternatives: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(255))
    decision_note: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    authorization_budget_version: Mapped[int | None] = mapped_column(Integer)
    authorization_monthly_limit: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowRun(Timestamped, Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('accepted', 'queued', 'running', 'cancellation_requested', "
            "'succeeded', 'failed', 'cancelled')",
            name="ck_workflow_runs_status",
        ),
        CheckConstraint(
            "char_length(btrim(workflow_kind)) > 0",
            name="ck_workflow_runs_kind",
        ),
        CheckConstraint(
            "char_length(btrim(idempotency_key)) > 0",
            name="ck_workflow_runs_idempotency_key",
        ),
        CheckConstraint(
            "temporal_workflow_id IS NULL OR char_length(btrim(temporal_workflow_id)) > 0",
            name="ck_workflow_runs_temporal_id",
        ),
        CheckConstraint(
            "cost_estimate IS NULL OR cost_estimate >= 0",
            name="ck_workflow_runs_cost_estimate",
        ),
        CheckConstraint("version > 0", name="ck_workflow_runs_version"),
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_workflow_runs_project_idempotency",
        ),
        Index("ix_workflow_runs_project_status", "project_id", "status"),
        Index("ix_workflow_runs_retry_of_run_id", "retry_of_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_kind: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    input_payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="accepted", nullable=False)
    temporal_workflow_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    retry_of_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL")
    )
    cost_estimate: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowStep(Timestamped, Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled', 'skipped')",
            name="ck_workflow_steps_status",
        ),
        CheckConstraint("char_length(btrim(key)) > 0", name="ck_workflow_steps_key"),
        CheckConstraint("char_length(btrim(name)) > 0", name="ck_workflow_steps_name"),
        CheckConstraint("position >= 0", name="ck_workflow_steps_position"),
        CheckConstraint("version > 0", name="ck_workflow_steps_version"),
        UniqueConstraint("workflow_run_id", "key", name="uq_workflow_steps_run_key"),
        UniqueConstraint("workflow_run_id", "position", name="uq_workflow_steps_run_position"),
        Index("ix_workflow_steps_run_status", "workflow_run_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )


class WorkflowStepAttempt(Base):
    __tablename__ = "workflow_step_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('succeeded', 'failed', 'cancelled')",
            name="ck_workflow_step_attempts_status",
        ),
        CheckConstraint("attempt_number > 0", name="ck_workflow_step_attempts_number"),
        CheckConstraint(
            "(status = 'succeeded' AND result_payload IS NOT NULL AND error_payload IS NULL) "
            "OR (status = 'failed' AND error_payload IS NOT NULL) "
            "OR status = 'cancelled'",
            name="ck_workflow_step_attempts_payload",
        ),
        CheckConstraint(
            "completed_at >= started_at",
            name="ck_workflow_step_attempts_time_order",
        ),
        UniqueConstraint(
            "workflow_step_id",
            "attempt_number",
            name="uq_workflow_step_attempts_step_number",
        ),
        Index("ix_workflow_step_attempts_step_id", "workflow_step_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    result_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB(none_as_null=True))
    error_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB(none_as_null=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    object_type: Mapped[str] = mapped_column(String(120), nullable=False)
    object_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('validation', 'source_control', 'workflow', 'other')", name="ck_evidence_kind"
        ),
        CheckConstraint("char_length(btrim(name)) > 0", name="ck_evidence_name"),
        CheckConstraint("char_length(btrim(content_type)) > 0", name="ck_evidence_content_type"),
        CheckConstraint(
            "object_key ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'", name="ck_evidence_object_key"
        ),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_evidence_sha256"),
        CheckConstraint("size_bytes >= 0", name="ck_evidence_size_bytes"),
        CheckConstraint(
            "retention_class IN ('transient', 'standard', 'compliance', 'permanent')",
            name="ck_evidence_retention_class",
        ),
        CheckConstraint(
            "(retention_class = 'permanent' AND retain_until IS NULL) "
            "OR (retention_class <> 'permanent' AND retain_until IS NOT NULL "
            "AND retain_until > created_at)",
            name="ck_evidence_retention_deadline",
        ),
        UniqueConstraint("project_id", "object_key", name="uq_evidence_project_object_key"),
        Index("ix_evidence_project_created", "project_id", "created_at"),
        Index("ix_evidence_workflow_run_id", "workflow_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL")
    )
    workflow_step_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_step_attempts.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    content_type: Mapped[str] = mapped_column(String(200), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    retention_class: Mapped[str] = mapped_column(String(30), nullable=False)
    retain_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
