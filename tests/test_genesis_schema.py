from devsembly import models  # noqa: F401
from devsembly.database import Base


def test_genesis_tables_are_registered() -> None:
    assert {
        "organizations",
        "principals",
        "external_identities",
        "organization_memberships",
        "authorization_delegations",
        "initiatives",
        "projects",
        "budgets",
        "cost_evaluations",
        "decisions",
        "workflow_runs",
        "workflow_steps",
        "workflow_step_attempts",
        "audit_events",
        "evidence",
        "outbox_events",
        "published_events",
        "worker_heartbeats",
    }.issubset(Base.metadata.tables)


def test_identity_keys_and_membership_scope_are_unique() -> None:
    external_constraints = Base.metadata.tables["external_identities"].constraints
    membership_constraints = Base.metadata.tables["organization_memberships"].constraints
    assert any(
        constraint.name == "uq_external_identities_issuer_subject"
        for constraint in external_constraints
    )
    assert any(
        constraint.name == "uq_organization_memberships_org_principal"
        for constraint in membership_constraints
    )


def test_workflow_id_is_unique() -> None:
    column = Base.metadata.tables["workflow_runs"].c.temporal_workflow_id
    assert column.unique is True
    assert column.nullable is True


def test_budget_uses_fixed_precision_money() -> None:
    column = Base.metadata.tables["budgets"].c.monthly_limit
    assert column.type.precision == 12
    assert column.type.scale == 2


def test_mutable_genesis_aggregates_use_optimistic_versions() -> None:
    for table_name in (
        "organizations",
        "initiatives",
        "projects",
        "budgets",
        "decisions",
        "workflow_runs",
        "workflow_steps",
    ):
        column = Base.metadata.tables[table_name].c.version
        assert column.nullable is False
        assert str(column.server_default.arg) == "1"


def test_one_budget_is_allowed_per_project() -> None:
    constraints = Base.metadata.tables["budgets"].constraints
    assert any(constraint.name == "uq_budgets_project_id" for constraint in constraints)


def test_workflow_idempotency_and_attempt_numbers_are_unique() -> None:
    run_constraints = Base.metadata.tables["workflow_runs"].constraints
    attempt_constraints = Base.metadata.tables["workflow_step_attempts"].constraints
    assert any(
        constraint.name == "uq_workflow_runs_project_idempotency" for constraint in run_constraints
    )
    assert any(
        constraint.name == "uq_workflow_step_attempts_step_number"
        for constraint in attempt_constraints
    )


def test_workflow_attempt_optional_payloads_store_sql_null() -> None:
    table = Base.metadata.tables["workflow_step_attempts"]
    assert table.c.result_payload.type.none_as_null is True
    assert table.c.error_payload.type.none_as_null is True


def test_cost_governance_money_and_idempotency_constraints() -> None:
    table = Base.metadata.tables["cost_evaluations"]
    assert table.c.selected_monthly_cost.type.precision == 14
    assert table.c.selected_monthly_cost.type.scale == 4
    assert table.c.recommendation.type.none_as_null is True
    assert any(
        constraint.name == "uq_cost_evaluations_project_idempotency"
        for constraint in table.constraints
    )


def test_decisions_have_final_state_and_budget_authorization_fields() -> None:
    table = Base.metadata.tables["decisions"]
    assert table.c.cost_evaluation_id.nullable is True
    assert table.c.decided_at.nullable is True
    assert table.c.authorization_budget_version.nullable is True
    assert table.c.estimated_monthly_cost.type.precision == 14
    assert table.c.estimated_monthly_cost.type.scale == 4


def test_evidence_retention_is_server_governed() -> None:
    table = Base.metadata.tables["evidence"]
    assert table.c.retention_class.nullable is False
    assert table.c.retain_until.nullable is True
    assert any(
        constraint.name == "ck_evidence_retention_deadline" for constraint in table.constraints
    )


def test_outbox_publication_and_audit_columns_are_registered() -> None:
    outbox = Base.metadata.tables["outbox_events"]
    audit = Base.metadata.tables["audit_events"]
    published = Base.metadata.tables["published_events"]
    assert outbox.c.attempt_count.nullable is False
    assert outbox.c.available_at.nullable is False
    assert published.c.event_id.primary_key is True
    assert audit.c.outcome.nullable is False
    assert audit.c.correlation_id.nullable is True
