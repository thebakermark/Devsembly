from devsembly import models  # noqa: F401
from devsembly.database import Base


def test_genesis_tables_are_registered() -> None:
    assert {
        "organizations",
        "initiatives",
        "projects",
        "budgets",
        "decisions",
        "workflow_runs",
        "audit_events",
        "outbox_events",
    }.issubset(Base.metadata.tables)


def test_workflow_id_is_unique() -> None:
    column = Base.metadata.tables["workflow_runs"].c.temporal_workflow_id
    assert column.unique is True


def test_budget_uses_fixed_precision_money() -> None:
    column = Base.metadata.tables["budgets"].c.monthly_limit
    assert column.type.precision == 12
    assert column.type.scale == 2


def test_mutable_genesis_aggregates_use_optimistic_versions() -> None:
    for table_name in ("organizations", "initiatives", "projects", "budgets"):
        column = Base.metadata.tables[table_name].c.version
        assert column.nullable is False
        assert str(column.server_default.arg) == "1"


def test_one_budget_is_allowed_per_project() -> None:
    constraints = Base.metadata.tables["budgets"].constraints
    assert any(constraint.name == "uq_budgets_project_id" for constraint in constraints)
