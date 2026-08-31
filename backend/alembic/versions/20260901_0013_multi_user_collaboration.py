"""Add V2.1 project memberships, comments, notifications, and display names."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0013"
down_revision: str | None = "20260831_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps():
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
    op.add_column("users", sa.Column("display_name", sa.String(120), nullable=True))
    op.create_table(
        "project_memberships",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "OWNER",
                "PROJECT_ADMIN",
                "PROJECT_MANAGER",
                "CONTRIBUTOR",
                "VIEWER",
                name="project_access_role",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "INVITED", "DISABLED", name="membership_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["project_id", "person_id"],
            ["project_members.project_id", "project_members.person_id"],
            name="fk_project_membership_project_person",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_membership_user"),
        sa.UniqueConstraint("project_id", "person_id", name="uq_project_membership_person"),
    )
    op.create_index(
        "ix_project_memberships_user_status", "project_memberships", ["user_id", "status"]
    )
    op.create_index(
        "ix_project_memberships_project_role",
        "project_memberships",
        ["project_id", "role", "status"],
    )
    op.execute(
        sa.text("""
        INSERT INTO project_memberships
            (id, project_id, user_id, person_id, role, status, joined_at, invited_at,
             created_by_user_id, created_at, updated_at)
        SELECT id, id, owner_user_id, NULL, 'OWNER', 'ACTIVE', created_at, NULL,
               owner_user_id, created_at, updated_at
        FROM projects
    """)
    )
    op.create_table(
        "collaboration_comments",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum(
                "TASK",
                "RISK",
                "ISSUE",
                "CHANGE_REQUEST",
                "MEETING",
                "DECISION",
                name="comment_entity_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("length(body) > 0", name="ck_collaboration_comment_body"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_collaboration_comments_target",
        "collaboration_comments",
        ["project_id", "entity_type", "entity_id", "created_at"],
    )
    op.create_table(
        "notifications",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "TASK_ASSIGNED",
                "COMMENT_ADDED",
                "MENTIONED",
                "MEMBER_ADDED",
                "ROLE_CHANGED",
                "MEETING_ACTION_ASSIGNED",
                "RISK_ASSIGNED",
                "ISSUE_ASSIGNED",
                name="notification_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_read", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_collaboration_comments_target", table_name="collaboration_comments")
    op.drop_table("collaboration_comments")
    op.drop_index("ix_project_memberships_project_role", table_name="project_memberships")
    op.drop_index("ix_project_memberships_user_status", table_name="project_memberships")
    op.drop_table("project_memberships")
    op.drop_column("users", "display_name")
