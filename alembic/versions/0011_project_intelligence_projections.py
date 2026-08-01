"""Add PIE work-item, alias, and graph projections.

Revision ID: 0011_pie_projections
Revises: 0010_project_intelligence
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_pie_projections"
down_revision = "0010_project_intelligence"
branch_labels = None
depends_on = None


def _source_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("source_provider", sa.String(80), nullable=False),
        sa.Column("source_kind", sa.String(80), nullable=False),
        sa.Column("source_external_id", sa.String(500)),
        sa.Column("source_uri", sa.String(1000)),
        sa.Column("source_occurred_at", sa.DateTime(timezone=True)),
        sa.Column("source_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assertion_status", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence_explanation", sa.Text(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "project_intelligence_projections",
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "source_revision_id",
            sa.UUID(),
            sa.ForeignKey("project_state_revisions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("rebuilt_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_intelligence_work_items",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stable_id", sa.String(240), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("parent_stable_id", sa.String(240)),
        sa.Column(
            "source_revision_id",
            sa.UUID(),
            sa.ForeignKey("project_state_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *_source_columns(),
        sa.CheckConstraint(
            "kind IN ('roadmap', 'milestone', 'epic', 'feature', 'task', 'sprint')",
            name="ck_project_intelligence_work_items_kind",
        ),
        sa.CheckConstraint(
            "assertion_status IN ('verified', 'inferred', 'disputed')",
            name="ck_project_intelligence_work_items_assertion",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_project_intelligence_work_items_confidence",
        ),
        sa.UniqueConstraint("project_id", "stable_id", name="uq_pie_work_item_stable_id"),
    )
    op.create_index(
        "ix_pie_work_items_project_kind", "project_intelligence_work_items", ["project_id", "kind"]
    )
    op.create_table(
        "project_intelligence_provider_aliases",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canonical_id", sa.String(240), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("account", sa.String(240), nullable=False),
        sa.Column("external_kind", sa.String(80), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("uri", sa.String(1000)),
        sa.Column(
            "source_revision_id",
            sa.UUID(),
            sa.ForeignKey("project_state_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "project_id",
            "provider",
            "account",
            "external_kind",
            "external_id",
            name="uq_pie_provider_alias_scope",
        ),
    )
    op.create_index(
        "ix_pie_alias_canonical",
        "project_intelligence_provider_aliases",
        ["project_id", "canonical_id"],
    )
    op.create_table(
        "project_intelligence_graph_nodes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stable_id", sa.String(240), nullable=False),
        sa.Column("graph_kind", sa.String(20), nullable=False),
        sa.Column("entity_kind", sa.String(80), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column(
            "source_revision_id",
            sa.UUID(),
            sa.ForeignKey("project_state_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *_source_columns(),
        sa.CheckConstraint(
            "graph_kind IN ('capability', 'dependency')",
            name="ck_project_intelligence_graph_nodes_kind",
        ),
        sa.CheckConstraint(
            "assertion_status IN ('verified', 'inferred', 'disputed')",
            name="ck_project_intelligence_graph_nodes_assertion",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_project_intelligence_graph_nodes_confidence",
        ),
        sa.UniqueConstraint(
            "project_id", "graph_kind", "stable_id", name="uq_pie_graph_node_stable_id"
        ),
    )
    op.create_table(
        "project_intelligence_graph_edges",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stable_id", sa.String(240), nullable=False),
        sa.Column("graph_kind", sa.String(20), nullable=False),
        sa.Column("from_stable_id", sa.String(240), nullable=False),
        sa.Column("to_stable_id", sa.String(240), nullable=False),
        sa.Column("relationship", sa.String(40), nullable=False),
        sa.Column(
            "source_revision_id",
            sa.UUID(),
            sa.ForeignKey("project_state_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *_source_columns(),
        sa.CheckConstraint(
            "graph_kind IN ('capability', 'dependency')",
            name="ck_project_intelligence_graph_edges_kind",
        ),
        sa.CheckConstraint(
            "relationship IN ('parent_of', 'depends_on', 'implements', 'validates', 'evidences', 'blocks', 'supersedes', 'derived_from')",
            name="ck_project_intelligence_graph_edges_relationship",
        ),
        sa.CheckConstraint(
            "assertion_status IN ('verified', 'inferred', 'disputed')",
            name="ck_project_intelligence_graph_edges_assertion",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_project_intelligence_graph_edges_confidence",
        ),
        sa.UniqueConstraint(
            "project_id", "graph_kind", "stable_id", name="uq_pie_graph_edge_stable_id"
        ),
    )
    op.create_index(
        "ix_pie_graph_edge_from",
        "project_intelligence_graph_edges",
        ["project_id", "graph_kind", "from_stable_id"],
    )
    op.create_index(
        "ix_pie_graph_edge_to",
        "project_intelligence_graph_edges",
        ["project_id", "graph_kind", "to_stable_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pie_graph_edge_to", table_name="project_intelligence_graph_edges")
    op.drop_index("ix_pie_graph_edge_from", table_name="project_intelligence_graph_edges")
    op.drop_table("project_intelligence_graph_edges")
    op.drop_table("project_intelligence_graph_nodes")
    op.drop_index("ix_pie_alias_canonical", table_name="project_intelligence_provider_aliases")
    op.drop_table("project_intelligence_provider_aliases")
    op.drop_index("ix_pie_work_items_project_kind", table_name="project_intelligence_work_items")
    op.drop_table("project_intelligence_work_items")
    op.drop_table("project_intelligence_projections")
