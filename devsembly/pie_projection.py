from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation

from devsembly.domain import (
    ProjectGraphEdge,
    ProjectGraphKind,
    ProjectGraphNode,
    ProjectIntelligenceProjection,
    ProjectProjectionCheckpoint,
    ProjectProviderAlias,
    ProjectRisk,
    ProjectStateAssertionStatus,
    ProjectStateRevision,
    ProjectTechnicalDebt,
    ProjectValidationResult,
    ProjectWorkItem,
    ProjectWorkItemKind,
)
from devsembly.errors import ProjectStateValidationError

_WORK_ITEM_COLLECTIONS = {
    "roadmap": ProjectWorkItemKind.ROADMAP,
    "milestones": ProjectWorkItemKind.MILESTONE,
    "epics": ProjectWorkItemKind.EPIC,
    "features": ProjectWorkItemKind.FEATURE,
    "tasks": ProjectWorkItemKind.TASK,
}
_RELATIONSHIPS = {
    "parent_of",
    "depends_on",
    "implements",
    "validates",
    "evidences",
    "blocks",
    "supersedes",
    "derived_from",
}
_ALLOWED_PARENT_KINDS: dict[ProjectWorkItemKind, set[ProjectWorkItemKind]] = {
    ProjectWorkItemKind.ROADMAP: set(),
    ProjectWorkItemKind.MILESTONE: {ProjectWorkItemKind.ROADMAP},
    ProjectWorkItemKind.EPIC: {ProjectWorkItemKind.MILESTONE},
    ProjectWorkItemKind.FEATURE: {ProjectWorkItemKind.EPIC},
    ProjectWorkItemKind.TASK: {ProjectWorkItemKind.EPIC, ProjectWorkItemKind.FEATURE},
    ProjectWorkItemKind.SPRINT: set(),
}


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ProjectStateValidationError(f"{path} must be an object")
    return value


def _text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectStateValidationError(f"{path} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _text(value, path)


def _datetime(value: object, path: str, *, optional: bool) -> datetime | None:
    if value is None and optional:
        return None
    text = _text(value, path)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ProjectStateValidationError(f"{path} must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        raise ProjectStateValidationError(f"{path} must include a timezone")
    return parsed


def _list(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise ProjectStateValidationError(f"{path} must be an array")
    return value


def _decimal(value: object, path: str, *, minimum: int = 0, maximum: int | None = None) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ProjectStateValidationError(f"{path} must be numeric") from exc
    if result < minimum or (maximum is not None and result > maximum):
        limit = (
            f" between {minimum} and {maximum}" if maximum is not None else f" at least {minimum}"
        )
        raise ProjectStateValidationError(f"{path} must be{limit}")
    return result


def _text_list(value: object, path: str) -> tuple[str, ...]:
    items = tuple(_text(item, f"{path}[{index}]") for index, item in enumerate(_list(value, path)))
    if len(items) != len(set(items)):
        raise ProjectStateValidationError(f"{path} must not contain duplicates")
    return items


def _assertion(
    item: Mapping[str, object], path: str
) -> tuple[ProjectStateAssertionStatus, Decimal, str]:
    value = _mapping(item.get("confidence"), f"{path}.confidence")
    try:
        status = ProjectStateAssertionStatus(
            _text(value.get("status"), f"{path}.confidence.status")
        )
    except ValueError as exc:
        raise ProjectStateValidationError(
            f"{path}.confidence.status must be verified, inferred, or disputed"
        ) from exc
    try:
        score = Decimal(str(value.get("score")))
    except (InvalidOperation, ValueError) as exc:
        raise ProjectStateValidationError(f"{path}.confidence.score must be numeric") from exc
    if score < 0 or score > 1:
        raise ProjectStateValidationError(f"{path}.confidence.score must be between 0 and 1")
    explanation = _text(value.get("explanation"), f"{path}.confidence.explanation")
    return status, score, explanation


def _provenance(
    item: Mapping[str, object], path: str
) -> tuple[str, str, str | None, str | None, datetime | None, datetime]:
    value = _mapping(item.get("provenance"), f"{path}.provenance")
    observed_at = _datetime(
        value.get("observed_at"), f"{path}.provenance.observed_at", optional=False
    )
    assert observed_at is not None
    return (
        _text(value.get("provider"), f"{path}.provenance.provider"),
        _text(value.get("kind"), f"{path}.provenance.kind"),
        _optional_text(value.get("external_id"), f"{path}.provenance.external_id"),
        _optional_text(value.get("uri"), f"{path}.provenance.uri"),
        _datetime(value.get("occurred_at"), f"{path}.provenance.occurred_at", optional=True),
        observed_at,
    )


def _aliases(
    item: Mapping[str, object],
    path: str,
    project_id: uuid.UUID,
    stable_id: str,
    revision_id: uuid.UUID,
) -> list[ProjectProviderAlias]:
    aliases: list[ProjectProviderAlias] = []
    for index, raw in enumerate(_list(item.get("aliases", []), f"{path}.aliases")):
        alias_path = f"{path}.aliases[{index}]"
        alias = _mapping(raw, alias_path)
        aliases.append(
            ProjectProviderAlias(
                id=uuid.uuid4(),
                project_id=project_id,
                canonical_id=stable_id,
                provider=_text(alias.get("provider"), f"{alias_path}.provider"),
                account=_text(alias.get("account"), f"{alias_path}.account"),
                external_kind=_text(alias.get("kind"), f"{alias_path}.kind"),
                external_id=_text(alias.get("external_id"), f"{alias_path}.external_id"),
                uri=_optional_text(alias.get("uri"), f"{alias_path}.uri"),
                source_revision_id=revision_id,
            )
        )
    return aliases


def _ensure_acyclic(edges: Iterable[tuple[str, str]], label: str) -> None:
    outgoing: dict[str, set[str]] = {}
    for source, target in edges:
        outgoing.setdefault(source, set()).add(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ProjectStateValidationError(f"{label} contains a cycle at {node!r}")
        if node in visited:
            return
        visiting.add(node)
        for target in sorted(outgoing.get(node, set())):
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(outgoing):
        visit(node)


def build_projection(
    revision: ProjectStateRevision, rebuilt_at: datetime
) -> ProjectIntelligenceProjection:
    state = revision.state
    planning_value = state.get("planning", {})
    planning = _mapping(planning_value, "state.planning")
    work_items: list[ProjectWorkItem] = []
    aliases: list[ProjectProviderAlias] = []

    def add_work_item(raw: object, kind: ProjectWorkItemKind, path: str) -> None:
        item = _mapping(raw, path)
        stable_id = _text(item.get("id"), f"{path}.id")
        provider, source_kind, external_id, uri, occurred_at, observed_at = _provenance(item, path)
        assertion_status, confidence, explanation = _assertion(item, path)
        work_items.append(
            ProjectWorkItem(
                id=uuid.uuid4(),
                project_id=revision.project_id,
                stable_id=stable_id,
                kind=kind,
                title=_text(item.get("title"), f"{path}.title"),
                status=_text(item.get("status"), f"{path}.status"),
                parent_stable_id=_optional_text(item.get("parent_id"), f"{path}.parent_id"),
                source_revision_id=revision.id,
                source_provider=provider,
                source_kind=source_kind,
                source_external_id=external_id,
                source_uri=uri,
                source_occurred_at=occurred_at,
                source_observed_at=observed_at,
                assertion_status=assertion_status,
                confidence=confidence,
                confidence_explanation=explanation,
            )
        )
        aliases.extend(_aliases(item, path, revision.project_id, stable_id, revision.id))

    for collection, kind in _WORK_ITEM_COLLECTIONS.items():
        for index, raw in enumerate(
            _list(planning.get(collection, []), f"state.planning.{collection}")
        ):
            add_work_item(raw, kind, f"state.planning.{collection}[{index}]")
    current_sprint = planning.get("current_sprint")
    if current_sprint is not None:
        add_work_item(current_sprint, ProjectWorkItemKind.SPRINT, "state.planning.current_sprint")

    work_ids = [item.stable_id for item in work_items]
    if len(work_ids) != len(set(work_ids)):
        raise ProjectStateValidationError("work item stable IDs must be unique within a project")
    work_id_set = set(work_ids)
    work_kind_by_id = {item.stable_id: item.kind for item in work_items}
    parent_edges: list[tuple[str, str]] = []
    for item in work_items:
        if item.parent_stable_id is None:
            continue
        if item.parent_stable_id not in work_id_set:
            raise ProjectStateValidationError(
                f"work item {item.stable_id!r} has an unknown or cross-project parent"
            )
        if item.parent_stable_id == item.stable_id:
            raise ProjectStateValidationError(f"work item {item.stable_id!r} cannot parent itself")
        parent_kind = work_kind_by_id[item.parent_stable_id]
        if parent_kind not in _ALLOWED_PARENT_KINDS[item.kind]:
            raise ProjectStateValidationError(
                f"{item.kind.value} {item.stable_id!r} cannot have a {parent_kind.value} parent"
            )
        parent_edges.append((item.parent_stable_id, item.stable_id))
    _ensure_acyclic(parent_edges, "work item hierarchy")

    graphs = _mapping(state.get("graphs", {}), "state.graphs")
    nodes: list[ProjectGraphNode] = []
    edges: list[ProjectGraphEdge] = []
    for key, graph_kind in (
        ("capabilities", ProjectGraphKind.CAPABILITY),
        ("dependencies", ProjectGraphKind.DEPENDENCY),
    ):
        graph = _mapping(graphs.get(key, {}), f"state.graphs.{key}")
        graph_nodes = _list(graph.get("nodes", []), f"state.graphs.{key}.nodes")
        graph_edges = _list(graph.get("edges", []), f"state.graphs.{key}.edges")
        graph_node_ids: set[str] = set()
        for index, raw in enumerate(graph_nodes):
            path = f"state.graphs.{key}.nodes[{index}]"
            node_data = _mapping(raw, path)
            stable_id = _text(node_data.get("id"), f"{path}.id")
            if stable_id in graph_node_ids:
                raise ProjectStateValidationError(
                    f"duplicate {graph_kind.value} node {stable_id!r}"
                )
            graph_node_ids.add(stable_id)
            provider, source_kind, external_id, uri, occurred_at, observed_at = _provenance(
                node_data, path
            )
            assertion_status, confidence, explanation = _assertion(node_data, path)
            nodes.append(
                ProjectGraphNode(
                    id=uuid.uuid4(),
                    project_id=revision.project_id,
                    stable_id=stable_id,
                    graph_kind=graph_kind,
                    entity_kind=_text(node_data.get("kind", graph_kind.value), f"{path}.kind"),
                    title=_text(node_data.get("title"), f"{path}.title"),
                    status=_text(node_data.get("status"), f"{path}.status"),
                    source_revision_id=revision.id,
                    source_provider=provider,
                    source_kind=source_kind,
                    source_external_id=external_id,
                    source_uri=uri,
                    source_occurred_at=occurred_at,
                    source_observed_at=observed_at,
                    assertion_status=assertion_status,
                    confidence=confidence,
                    confidence_explanation=explanation,
                )
            )
            aliases.extend(_aliases(node_data, path, revision.project_id, stable_id, revision.id))
        graph_pairs: list[tuple[str, str]] = []
        edge_ids: set[str] = set()
        for index, raw in enumerate(graph_edges):
            path = f"state.graphs.{key}.edges[{index}]"
            edge_data = _mapping(raw, path)
            stable_id = _text(edge_data.get("id"), f"{path}.id")
            if stable_id in edge_ids:
                raise ProjectStateValidationError(
                    f"duplicate {graph_kind.value} edge {stable_id!r}"
                )
            edge_ids.add(stable_id)
            source_id = _text(edge_data.get("from"), f"{path}.from")
            target_id = _text(edge_data.get("to"), f"{path}.to")
            if source_id not in graph_node_ids or target_id not in graph_node_ids:
                raise ProjectStateValidationError(
                    f"edge {stable_id!r} has an unknown or cross-project endpoint"
                )
            relationship = _text(edge_data.get("type"), f"{path}.type")
            if relationship not in _RELATIONSHIPS:
                raise ProjectStateValidationError(
                    f"edge {stable_id!r} has unsupported relationship {relationship!r}"
                )
            provider, source_kind, external_id, uri, occurred_at, observed_at = _provenance(
                edge_data, path
            )
            assertion_status, confidence, explanation = _assertion(edge_data, path)
            edges.append(
                ProjectGraphEdge(
                    id=uuid.uuid4(),
                    project_id=revision.project_id,
                    stable_id=stable_id,
                    graph_kind=graph_kind,
                    from_stable_id=source_id,
                    to_stable_id=target_id,
                    relationship=relationship,
                    source_revision_id=revision.id,
                    source_provider=provider,
                    source_kind=source_kind,
                    source_external_id=external_id,
                    source_uri=uri,
                    source_occurred_at=occurred_at,
                    source_observed_at=observed_at,
                    assertion_status=assertion_status,
                    confidence=confidence,
                    confidence_explanation=explanation,
                )
            )
            graph_pairs.append((source_id, target_id))
        _ensure_acyclic(graph_pairs, f"{graph_kind.value} graph")

    alias_keys = [
        (item.provider, item.account, item.external_kind, item.external_id) for item in aliases
    ]
    if len(alias_keys) != len(set(alias_keys)):
        raise ProjectStateValidationError("provider aliases must be unique within a project")

    capability_ids = {
        item.stable_id for item in nodes if item.graph_kind is ProjectGraphKind.CAPABILITY
    }
    dependency_ids = {
        item.stable_id for item in nodes if item.graph_kind is ProjectGraphKind.DEPENDENCY
    }
    validation_results: list[ProjectValidationResult] = []
    validation = _mapping(state.get("validation", {}), "state.validation")
    for index, raw in enumerate(_list(validation.get("results", []), "state.validation.results")):
        path = f"state.validation.results[{index}]"
        validation_data = _mapping(raw, path)
        evidence_ids = _text_list(validation_data.get("evidence_ids", []), f"{path}.evidence_ids")
        status = _text(validation_data.get("status"), f"{path}.status")
        if status in {"passed", "failed"} and not evidence_ids:
            raise ProjectStateValidationError(
                f"{path}.status must be unverified when no evidence_ids are supplied"
            )
        affected = _text_list(
            validation_data.get("affected_capability_ids", []), f"{path}.affected_capability_ids"
        )
        if not set(affected).issubset(capability_ids):
            raise ProjectStateValidationError(f"{path} references an unknown capability")
        provider, source_kind, external_id, uri, occurred_at, observed_at = _provenance(
            validation_data, path
        )
        assertion_status, confidence, explanation = _assertion(validation_data, path)
        validation_results.append(
            ProjectValidationResult(
                id=uuid.uuid4(),
                project_id=revision.project_id,
                stable_id=_text(validation_data.get("id"), f"{path}.id"),
                title=_text(validation_data.get("title"), f"{path}.title"),
                status=status,
                evidence_ids=evidence_ids,
                acceptance_criterion_ids=_text_list(
                    validation_data.get("acceptance_criterion_ids", []),
                    f"{path}.acceptance_criterion_ids",
                ),
                stale_at=_datetime(
                    validation_data.get("stale_at"), f"{path}.stale_at", optional=True
                ),
                superseded_by=_optional_text(
                    validation_data.get("superseded_by"), f"{path}.superseded_by"
                ),
                affected_capability_ids=affected,
                source_revision_id=revision.id,
                source_provider=provider,
                source_kind=source_kind,
                source_external_id=external_id,
                source_uri=uri,
                source_occurred_at=occurred_at,
                source_observed_at=observed_at,
                assertion_status=assertion_status,
                confidence=confidence,
                confidence_explanation=explanation,
            )
        )

    def impacts(item: Mapping[str, object], path: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        capabilities = _text_list(
            item.get("affected_capability_ids", []), f"{path}.affected_capability_ids"
        )
        dependencies = _text_list(
            item.get("affected_dependency_ids", []), f"{path}.affected_dependency_ids"
        )
        if not set(capabilities).issubset(capability_ids) or not set(dependencies).issubset(
            dependency_ids
        ):
            raise ProjectStateValidationError(
                f"{path} references an unknown capability or dependency"
            )
        return capabilities, dependencies

    risks: list[ProjectRisk] = []
    for index, raw in enumerate(_list(state.get("risks", []), "state.risks")):
        path = f"state.risks[{index}]"
        risk_data = _mapping(raw, path)
        capabilities, dependencies = impacts(risk_data, path)
        provider, source_kind, external_id, uri, occurred_at, observed_at = _provenance(
            risk_data, path
        )
        assertion_status, confidence, explanation = _assertion(risk_data, path)
        risks.append(
            ProjectRisk(
                id=uuid.uuid4(),
                project_id=revision.project_id,
                stable_id=_text(risk_data.get("id"), f"{path}.id"),
                title=_text(risk_data.get("title"), f"{path}.title"),
                status=_text(risk_data.get("status"), f"{path}.status"),
                owner_id=_text(risk_data.get("owner_id"), f"{path}.owner_id"),
                likelihood=_decimal(risk_data.get("likelihood"), f"{path}.likelihood", maximum=1),
                impact=_decimal(risk_data.get("impact"), f"{path}.impact", maximum=1),
                mitigation=_text(risk_data.get("mitigation"), f"{path}.mitigation"),
                trigger=_text(risk_data.get("trigger"), f"{path}.trigger"),
                review_at=_datetime(risk_data.get("review_at"), f"{path}.review_at", optional=True),
                affected_capability_ids=capabilities,
                affected_dependency_ids=dependencies,
                source_revision_id=revision.id,
                source_provider=provider,
                source_kind=source_kind,
                source_external_id=external_id,
                source_uri=uri,
                source_occurred_at=occurred_at,
                source_observed_at=observed_at,
                assertion_status=assertion_status,
                confidence=confidence,
                confidence_explanation=explanation,
            )
        )

    technical_debt: list[ProjectTechnicalDebt] = []
    for index, raw in enumerate(_list(state.get("technical_debt", []), "state.technical_debt")):
        path = f"state.technical_debt[{index}]"
        debt_data = _mapping(raw, path)
        capabilities, dependencies = impacts(debt_data, path)
        provider, source_kind, external_id, uri, occurred_at, observed_at = _provenance(
            debt_data, path
        )
        assertion_status, confidence, explanation = _assertion(debt_data, path)
        technical_debt.append(
            ProjectTechnicalDebt(
                id=uuid.uuid4(),
                project_id=revision.project_id,
                stable_id=_text(debt_data.get("id"), f"{path}.id"),
                title=_text(debt_data.get("title"), f"{path}.title"),
                status=_text(debt_data.get("status"), f"{path}.status"),
                owner_id=_text(debt_data.get("owner_id"), f"{path}.owner_id"),
                principal=_decimal(debt_data.get("principal"), f"{path}.principal"),
                interest=_decimal(debt_data.get("interest"), f"{path}.interest"),
                impact=_text(debt_data.get("impact"), f"{path}.impact"),
                retirement_criteria=_text(
                    debt_data.get("retirement_criteria"), f"{path}.retirement_criteria"
                ),
                affected_capability_ids=capabilities,
                affected_dependency_ids=dependencies,
                source_revision_id=revision.id,
                source_provider=provider,
                source_kind=source_kind,
                source_external_id=external_id,
                source_uri=uri,
                source_occurred_at=occurred_at,
                source_observed_at=observed_at,
                assertion_status=assertion_status,
                confidence=confidence,
                confidence_explanation=explanation,
            )
        )

    for label, values in (
        ("validation", validation_results),
        ("risk", risks),
        ("technical debt", technical_debt),
    ):
        stable_ids = [item.stable_id for item in values]
        if len(stable_ids) != len(set(stable_ids)):
            raise ProjectStateValidationError(f"{label} stable IDs must be unique within a project")

    return ProjectIntelligenceProjection(
        checkpoint=ProjectProjectionCheckpoint(
            project_id=revision.project_id,
            source_revision_id=revision.id,
            source_version=revision.version,
            rebuilt_at=rebuilt_at,
        ),
        work_items=tuple(work_items),
        aliases=tuple(aliases),
        graph_nodes=tuple(nodes),
        graph_edges=tuple(edges),
        validation_results=tuple(validation_results),
        risks=tuple(risks),
        technical_debt=tuple(technical_debt),
    )
