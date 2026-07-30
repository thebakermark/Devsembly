from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from devsembly.database import SessionFactory
from devsembly.repositories import (
    BudgetRepository,
    CostEvaluationRepository,
    DecisionRepository,
    InitiativeRepository,
    OrganizationRepository,
    OutboxRepository,
    ProjectRepository,
    WorkflowRunRepository,
    WorkflowStepAttemptRepository,
    WorkflowStepRepository,
)
from devsembly.sqlalchemy_repositories import (
    SqlAlchemyBudgetRepository,
    SqlAlchemyCostEvaluationRepository,
    SqlAlchemyDecisionRepository,
    SqlAlchemyInitiativeRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyOutboxRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyWorkflowRunRepository,
    SqlAlchemyWorkflowStepAttemptRepository,
    SqlAlchemyWorkflowStepRepository,
)


class UnitOfWork(Protocol):
    @property
    def organizations(self) -> OrganizationRepository: ...

    @property
    def initiatives(self) -> InitiativeRepository: ...

    @property
    def projects(self) -> ProjectRepository: ...

    @property
    def budgets(self) -> BudgetRepository: ...

    @property
    def cost_evaluations(self) -> CostEvaluationRepository: ...

    @property
    def decisions(self) -> DecisionRepository: ...

    @property
    def workflow_runs(self) -> WorkflowRunRepository: ...

    @property
    def workflow_steps(self) -> WorkflowStepRepository: ...

    @property
    def workflow_step_attempts(self) -> WorkflowStepAttemptRepository: ...

    @property
    def outbox(self) -> OutboxRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._committed = False

    def _active_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of Work is not active")
        return self._session

    @property
    def organizations(self) -> OrganizationRepository:
        return SqlAlchemyOrganizationRepository(self._active_session())

    @property
    def initiatives(self) -> InitiativeRepository:
        return SqlAlchemyInitiativeRepository(self._active_session())

    @property
    def projects(self) -> ProjectRepository:
        return SqlAlchemyProjectRepository(self._active_session())

    @property
    def budgets(self) -> BudgetRepository:
        return SqlAlchemyBudgetRepository(self._active_session())

    @property
    def cost_evaluations(self) -> CostEvaluationRepository:
        return SqlAlchemyCostEvaluationRepository(self._active_session())

    @property
    def decisions(self) -> DecisionRepository:
        return SqlAlchemyDecisionRepository(self._active_session())

    @property
    def workflow_runs(self) -> WorkflowRunRepository:
        return SqlAlchemyWorkflowRunRepository(self._active_session())

    @property
    def workflow_steps(self) -> WorkflowStepRepository:
        return SqlAlchemyWorkflowStepRepository(self._active_session())

    @property
    def workflow_step_attempts(self) -> WorkflowStepAttemptRepository:
        return SqlAlchemyWorkflowStepAttemptRepository(self._active_session())

    @property
    def outbox(self) -> OutboxRepository:
        return SqlAlchemyOutboxRepository(self._active_session())

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of Work cannot be entered twice")
        self._session = self._session_factory()
        self._committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._active_session()
        try:
            if exc_type is not None or not self._committed:
                await session.rollback()
        finally:
            await session.close()
            self._session = None

    async def commit(self) -> None:
        await self._active_session().commit()
        self._committed = True

    async def rollback(self) -> None:
        await self._active_session().rollback()
        self._committed = False
