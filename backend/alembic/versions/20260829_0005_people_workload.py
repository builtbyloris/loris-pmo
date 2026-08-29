"""Add people, project members, task assignees, and stakeholders.

Revision ID: 20260829_0005
Revises: 20260829_0004
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0005"
down_revision: str | None = "20260829_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    project_role = sa.Enum(
        "PROJECT_MANAGER",
        "SPONSOR",
        "PRODUCT_OWNER",
        "TEAM_MEMBER",
        "DEVELOPER",
        "DESIGNER",
        "DATA_ANALYST",
        "QA_TESTER",
        "STAKEHOLDER",
        "OTHER",
        name="project_role",
        native_enum=False,
        create_constraint=True,
    )
    stakeholder_influence = sa.Enum(
        "LOW",
        "MEDIUM",
        "HIGH",
        name="stakeholder_influence",
        native_enum=False,
        create_constraint=True,
    )
    stakeholder_interest = sa.Enum(
        "LOW",
        "MEDIUM",
        "HIGH",
        name="stakeholder_interest",
        native_enum=False,
        create_constraint=True,
    )

    op.alter_column("audit_events", "project_id", existing_type=sa.Uuid(), nullable=True)

    op.create_table(
        "people",
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("department", sa.String(160), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], name="fk_people_owner_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_people"),
        sa.UniqueConstraint("owner_user_id", "id", name="uq_people_owner_id"),
    )
    op.create_index("ix_people_owner_email", "people", ["owner_user_id", "email"])
    op.create_index("ix_people_owner_name", "people", ["owner_user_id", "name"])

    op.create_table(
        "project_members",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("role", project_role, nullable=False),
        sa.Column("responsibilities", sa.Text(), nullable=True),
        sa.Column("availability_percent", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "availability_percent >= 0 AND availability_percent <= 100",
            name=op.f("ck_project_members_project_member_availability_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["people.id"],
            ondelete="CASCADE",
            name="fk_project_members_person_id_people",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_project_members_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_members"),
        sa.UniqueConstraint("project_id", "id", name="uq_project_members_project_id"),
        sa.UniqueConstraint("project_id", "person_id", name="uq_project_members_project_person"),
    )
    op.create_index("ix_project_members_project_role", "project_members", ["project_id", "role"])

    op.create_table(
        "stakeholders",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("organization", sa.String(200), nullable=True),
        sa.Column("role", sa.String(200), nullable=True),
        sa.Column("influence", stakeholder_influence, nullable=False),
        sa.Column("interest", stakeholder_interest, nullable=False),
        sa.Column("communication_frequency", sa.String(160), nullable=True),
        sa.Column("communication_channel", sa.String(160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "person_id IS NOT NULL OR (name IS NOT NULL AND length(trim(name)) > 0)",
            name=op.f("ck_stakeholders_stakeholder_identity_required"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["people.id"],
            ondelete="RESTRICT",
            name="fk_stakeholders_person_id_people",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_stakeholders_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stakeholders"),
    )
    op.create_index(
        "ix_stakeholders_project_matrix",
        "stakeholders",
        ["project_id", "influence", "interest"],
    )

    op.create_table(
        "task_assignees",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("project_member_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["project_id", "project_member_id"],
            ["project_members.project_id", "project_members.id"],
            ondelete="CASCADE",
            name="fk_task_assignees_project_member",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="CASCADE",
            name="fk_task_assignees_project_task",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_task_assignees"),
        sa.UniqueConstraint(
            "project_id",
            "task_id",
            "project_member_id",
            name="uq_task_assignees_task_member",
        ),
    )
    op.create_index(
        "ix_task_assignees_member", "task_assignees", ["project_id", "project_member_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_task_assignees_member", table_name="task_assignees")
    op.drop_table("task_assignees")
    op.drop_index("ix_stakeholders_project_matrix", table_name="stakeholders")
    op.drop_table("stakeholders")
    op.drop_index("ix_project_members_project_role", table_name="project_members")
    op.drop_table("project_members")
    op.drop_index("ix_people_owner_name", table_name="people")
    op.drop_index("ix_people_owner_email", table_name="people")
    op.drop_table("people")
    op.alter_column("audit_events", "project_id", existing_type=sa.Uuid(), nullable=False)
