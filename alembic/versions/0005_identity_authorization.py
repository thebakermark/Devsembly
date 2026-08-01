"""Add human identity and organization authorization.

Revision ID: 0005_identity_authorization
Revises: 0004_cost_governance
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_identity_authorization"
down_revision = "0004_cost_governance"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "principals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), server_default="human", nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("kind = 'human'", name="ck_principals_kind"),
        sa.CheckConstraint(
            "char_length(btrim(display_name)) > 0", name="ck_principals_display_name"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "external_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issuer", sa.String(length=500), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("char_length(btrim(issuer)) > 0", name="ck_external_identities_issuer"),
        sa.CheckConstraint(
            "char_length(btrim(subject)) > 0", name="ck_external_identities_subject"
        ),
        sa.ForeignKeyConstraint(["principal_id"], ["principals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issuer", "subject", name="uq_external_identities_issuer_subject"),
    )
    op.create_index(
        "ix_external_identities_principal_id",
        "external_identities",
        ["principal_id"],
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "role IN ('owner', 'administrator', 'operator', 'approver', 'viewer')",
            name="ck_organization_memberships_role",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'revoked')",
            name="ck_organization_memberships_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["principal_id"], ["principals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "principal_id",
            name="uq_organization_memberships_org_principal",
        ),
    )
    op.create_index(
        "ix_organization_memberships_principal_status",
        "organization_memberships",
        ["principal_id", "status"],
    )
    op.create_table(
        "authorization_delegations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grantor_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("char_length(btrim(action)) > 0", name="ck_delegations_action"),
        sa.CheckConstraint("expires_at > starts_at", name="ck_delegations_time_order"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grantor_principal_id"], ["principals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_principal_id"], ["principals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_delegations_recipient_active",
        "authorization_delegations",
        ["recipient_principal_id", "revoked_at"],
    )
    op.create_index(
        "ix_delegations_organization_id",
        "authorization_delegations",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_delegations_organization_id", table_name="authorization_delegations")
    op.drop_index("ix_delegations_recipient_active", table_name="authorization_delegations")
    op.drop_table("authorization_delegations")
    op.drop_index(
        "ix_organization_memberships_principal_status",
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")
    op.drop_index("ix_external_identities_principal_id", table_name="external_identities")
    op.drop_table("external_identities")
    op.drop_table("principals")
