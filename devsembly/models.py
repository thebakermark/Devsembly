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


class Decision(Timestamped, Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    selected_option: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_monthly_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    alternatives: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, default=list, nullable=False
    )


class WorkflowRun(Timestamped, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL")
    )
    temporal_workflow_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    cost_estimate: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))


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
