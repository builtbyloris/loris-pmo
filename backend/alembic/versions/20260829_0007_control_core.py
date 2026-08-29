"""Add risks, issues, and change requests.

Revision ID: 20260829_0007
Revises: 20260829_0006
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0007"
down_revision: str | None = "20260829_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "change_requests",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.String(length=200), nullable=True),
        sa.Column("requested_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PENDING",
                "APPROVED",
                "REJECTED",
                "IMPLEMENTED",
                "CANCELLED",
                name="change_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "scope_impact",
            sa.Enum(
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                name="change_scope_impact",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "schedule_impact",
            sa.Enum(
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                name="change_schedule_impact",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "budget_impact",
            sa.Enum(
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                name="change_budget_impact",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "resource_impact",
            sa.Enum(
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                name="change_resource_impact",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("estimated_delay_days", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("decision_date", sa.Date(), nullable=True),
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
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name=op.f("ck_change_requests_change_estimated_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "estimated_delay_days IS NULL OR estimated_delay_days >= 0",
            name=op.f("ck_change_requests_change_estimated_delay_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_change_requests_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_change_requests")),
        sa.UniqueConstraint("project_id", "id", name="uq_change_requests_project_id"),
    )
    op.create_index(
        "ix_change_requests_project_requested_date",
        "change_requests",
        ["project_id", "requested_date"],
        unique=False,
    )
    op.create_index(
        "ix_change_requests_project_status",
        "change_requests",
        ["project_id", "status"],
        unique=False,
    )
    op.create_table(
        "change_request_milestone_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("change_request_id", sa.Uuid(), nullable=False),
        sa.Column("milestone_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "change_request_id"],
            ["change_requests.project_id", "change_requests.id"],
            name="fk_change_request_milestone_links_project_change",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            name="fk_change_request_milestone_links_project_milestone",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "change_request_id",
            "milestone_id",
            name=op.f("pk_change_request_milestone_links"),
        ),
    )
    op.create_table(
        "issues",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=160), nullable=True),
        sa.Column(
            "priority",
            sa.Enum(
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="issue_priority",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "IN_ANALYSIS",
                "ACTION_PLANNED",
                "IN_PROGRESS",
                "RESOLVED",
                "CLOSED",
                name="issue_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("owner_member_id", sa.Uuid(), nullable=True),
        sa.Column("identified_date", sa.Date(), nullable=False),
        sa.Column(
            "schedule_impact",
            sa.Enum(
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                name="issue_schedule_impact",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "budget_impact",
            sa.Enum(
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                name="issue_budget_impact",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "scope_impact",
            sa.Enum(
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                name="issue_scope_impact",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "quality_impact",
            sa.Enum(
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                name="issue_quality_impact",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("estimated_delay_days", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("actual_delay_days", sa.Integer(), nullable=True),
        sa.Column("actual_cost", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
            "actual_cost IS NULL OR actual_cost >= 0",
            name=op.f("ck_issues_issue_actual_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "actual_delay_days IS NULL OR actual_delay_days >= 0",
            name=op.f("ck_issues_issue_actual_delay_nonnegative"),
        ),
        sa.CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name=op.f("ck_issues_issue_estimated_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "estimated_delay_days IS NULL OR estimated_delay_days >= 0",
            name=op.f("ck_issues_issue_estimated_delay_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "owner_member_id"],
            ["project_members.project_id", "project_members.id"],
            name="fk_issues_project_owner_member",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_issues_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_issues")),
        sa.UniqueConstraint("project_id", "id", name="uq_issues_project_id"),
    )
    op.create_index(
        "ix_issues_project_identified_date",
        "issues",
        ["project_id", "identified_date"],
        unique=False,
    )
    op.create_index(
        "ix_issues_project_priority", "issues", ["project_id", "priority"], unique=False
    )
    op.create_index("ix_issues_project_status", "issues", ["project_id", "status"], unique=False)
    op.create_table(
        "risks",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=160), nullable=True),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=False),
        sa.Column("owner_member_id", sa.Uuid(), nullable=True),
        sa.Column("mitigation", sa.Text(), nullable=True),
        sa.Column("contingency", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "IDENTIFIED",
                "MONITORING",
                "MITIGATING",
                "OCCURRED",
                "ACCEPTED",
                "CLOSED",
                name="risk_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("identified_date", sa.Date(), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=True),
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
        sa.CheckConstraint("impact >= 1 AND impact <= 5", name=op.f("ck_risks_risk_impact_valid")),
        sa.CheckConstraint(
            "probability >= 1 AND probability <= 5", name=op.f("ck_risks_risk_probability_valid")
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "owner_member_id"],
            ["project_members.project_id", "project_members.id"],
            name="fk_risks_project_owner_member",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_risks_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risks")),
        sa.UniqueConstraint("project_id", "id", name="uq_risks_project_id"),
    )
    op.create_index(
        "ix_risks_project_matrix", "risks", ["project_id", "probability", "impact"], unique=False
    )
    op.create_index(
        "ix_risks_project_review_date", "risks", ["project_id", "review_date"], unique=False
    )
    op.create_index("ix_risks_project_status", "risks", ["project_id", "status"], unique=False)
    op.create_table(
        "change_request_issue_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("change_request_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "change_request_id"],
            ["change_requests.project_id", "change_requests.id"],
            name="fk_change_request_issue_links_project_change",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "issue_id"],
            ["issues.project_id", "issues.id"],
            name="fk_change_request_issue_links_project_issue",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "change_request_id",
            "issue_id",
            name=op.f("pk_change_request_issue_links"),
        ),
    )
    op.create_table(
        "change_request_risk_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("change_request_id", sa.Uuid(), nullable=False),
        sa.Column("risk_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "change_request_id"],
            ["change_requests.project_id", "change_requests.id"],
            name="fk_change_request_risk_links_project_change",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "risk_id"],
            ["risks.project_id", "risks.id"],
            name="fk_change_request_risk_links_project_risk",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "change_request_id", "risk_id", name=op.f("pk_change_request_risk_links")
        ),
    )
    op.create_table(
        "change_request_task_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("change_request_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "change_request_id"],
            ["change_requests.project_id", "change_requests.id"],
            name="fk_change_request_task_links_project_change",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_change_request_task_links_project_task",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "change_request_id", "task_id", name=op.f("pk_change_request_task_links")
        ),
    )
    op.create_table(
        "issue_milestone_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("milestone_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "issue_id"],
            ["issues.project_id", "issues.id"],
            name="fk_issue_milestone_links_project_issue",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            name="fk_issue_milestone_links_project_milestone",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "issue_id", "milestone_id", name=op.f("pk_issue_milestone_links")
        ),
    )
    op.create_table(
        "issue_task_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "issue_id"],
            ["issues.project_id", "issues.id"],
            name="fk_issue_task_links_project_issue",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_issue_task_links_project_task",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "issue_id", "task_id", name=op.f("pk_issue_task_links")
        ),
    )
    op.create_table(
        "risk_milestone_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("risk_id", sa.Uuid(), nullable=False),
        sa.Column("milestone_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "milestone_id"],
            ["milestones.project_id", "milestones.id"],
            name="fk_risk_milestone_links_project_milestone",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "risk_id"],
            ["risks.project_id", "risks.id"],
            name="fk_risk_milestone_links_project_risk",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "risk_id", "milestone_id", name=op.f("pk_risk_milestone_links")
        ),
    )
    op.create_table(
        "risk_task_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("risk_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "risk_id"],
            ["risks.project_id", "risks.id"],
            name="fk_risk_task_links_project_risk",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_risk_task_links_project_task",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "risk_id", "task_id", name=op.f("pk_risk_task_links")
        ),
    )


def downgrade() -> None:
    op.drop_table("risk_task_links")
    op.drop_table("risk_milestone_links")
    op.drop_table("issue_task_links")
    op.drop_table("issue_milestone_links")
    op.drop_table("change_request_task_links")
    op.drop_table("change_request_risk_links")
    op.drop_table("change_request_issue_links")
    op.drop_index("ix_risks_project_status", table_name="risks")
    op.drop_index("ix_risks_project_review_date", table_name="risks")
    op.drop_index("ix_risks_project_matrix", table_name="risks")
    op.drop_table("risks")
    op.drop_index("ix_issues_project_status", table_name="issues")
    op.drop_index("ix_issues_project_priority", table_name="issues")
    op.drop_index("ix_issues_project_identified_date", table_name="issues")
    op.drop_table("issues")
    op.drop_table("change_request_milestone_links")
    op.drop_index("ix_change_requests_project_status", table_name="change_requests")
    op.drop_index("ix_change_requests_project_requested_date", table_name="change_requests")
    op.drop_table("change_requests")
