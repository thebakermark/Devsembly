from devsembly.database import Base
from devsembly import models  # noqa: F401


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
