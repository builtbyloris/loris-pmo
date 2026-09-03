"""Add V2.4 user integration accounts and explicit project external links."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260904_0016"
down_revision: str | None = "20260903_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
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
    provider = sa.Enum("GOOGLE", "GITHUB", name="integration_provider", native_enum=False)
    account_status = sa.Enum(
        "CONNECTED",
        "REAUTH_REQUIRED",
        "ERROR",
        "DISCONNECTED",
        name="integration_account_status",
        native_enum=False,
    )
    kind = sa.Enum(
        "GOOGLE_CALENDAR",
        "GMAIL",
        "GITHUB_REPOSITORY",
        name="project_integration_kind",
        native_enum=False,
    )
    integration_status = sa.Enum(
        "ACTIVE", "STALE", "UNAVAILABLE", name="project_integration_status", native_enum=False
    )
    object_type = sa.Enum(
        "CALENDAR_EVENT",
        "EMAIL_MESSAGE",
        "GITHUB_ISSUE",
        "GITHUB_PULL_REQUEST",
        "GITHUB_COMMIT",
        name="external_object_type",
        native_enum=False,
    )
    visibility = sa.Enum(
        "PRIVATE", "PROJECT", "FINANCE", name="external_link_visibility", native_enum=False
    )

    op.create_table(
        "integration_accounts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", provider, nullable=False),
        sa.Column("provider_account_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", account_status, nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("safe_provider_metadata", sa.JSON(), nullable=False),
        sa.Column("encrypted_access_token", sa.Text()),
        sa.Column("encrypted_refresh_token", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "provider", "provider_account_id", name="uq_integration_account_identity"
        ),
    )
    op.create_index(
        "ix_integration_accounts_user_provider", "integration_accounts", ["user_id", "provider"]
    )

    op.create_table(
        "integration_oauth_states",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", provider, nullable=False),
        sa.Column("state_digest", sa.String(64), nullable=False),
        sa.Column("encrypted_code_verifier", sa.Text()),
        sa.Column("redirect_uri", sa.String(1000), nullable=False),
        sa.Column("return_path", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_digest", name="uq_integration_oauth_state_digest"),
    )
    op.create_index(
        "ix_integration_oauth_states_expiry",
        "integration_oauth_states",
        ["expires_at", "consumed_at"],
    )

    op.create_table(
        "project_integrations",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("integration_account_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", kind, nullable=False),
        sa.Column("external_resource_id", sa.String(500), nullable=False),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("status", integration_status, nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["integration_account_id"], ["integration_accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "kind", "external_resource_id", name="uq_project_integration_resource"
        ),
    )
    op.create_index(
        "ix_project_integrations_project_kind",
        "project_integrations",
        ["project_id", "kind", "status"],
    )

    op.create_table(
        "external_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("project_integration_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("object_type", object_type, nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("external_url", sa.String(2000), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("visibility", visibility, nullable=False),
        sa.Column("target_entity_type", sa.String(50), nullable=False),
        sa.Column("target_entity_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(50)),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["project_integration_id"], ["project_integrations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_integration_id",
            "object_type",
            "external_id",
            "target_entity_type",
            "target_entity_id",
            name="uq_external_link_target",
        ),
    )
    op.create_index(
        "ix_external_links_project_created", "external_links", ["project_id", "created_at"]
    )
    op.create_index(
        "ix_external_links_target",
        "external_links",
        ["project_id", "target_entity_type", "target_entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_external_links_target", table_name="external_links")
    op.drop_index("ix_external_links_project_created", table_name="external_links")
    op.drop_table("external_links")
    op.drop_index("ix_project_integrations_project_kind", table_name="project_integrations")
    op.drop_table("project_integrations")
    op.drop_index("ix_integration_oauth_states_expiry", table_name="integration_oauth_states")
    op.drop_table("integration_oauth_states")
    op.drop_index("ix_integration_accounts_user_provider", table_name="integration_accounts")
    op.drop_table("integration_accounts")
