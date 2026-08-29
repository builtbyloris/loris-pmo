from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class ProjectLogType(StrEnum):
    MEETING = "MEETING"
    DECISION = "DECISION"
    ISSUE = "ISSUE"
    CHANGE = "CHANGE"
    MILESTONE = "MILESTONE"
    TASK_UPDATE = "TASK_UPDATE"
    RISK_UPDATE = "RISK_UPDATE"
    NOTE = "NOTE"
    AI_EVENT = "AI_EVENT"


class MemorySource(StrEnum):
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


class MemoryEntityType(StrEnum):
    TASK = "TASK"
    MILESTONE = "MILESTONE"
    RISK = "RISK"
    ISSUE = "ISSUE"
    CHANGE_REQUEST = "CHANGE_REQUEST"
    MEETING = "MEETING"
    DECISION = "DECISION"


class MeetingStatus(StrEnum):
    PLANNED = "PLANNED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ActionItemStatus(StrEnum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"


class DecisionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    DECIDED = "DECIDED"
    REVERSED = "REVERSED"
    SUPERSEDED = "SUPERSEDED"


project_log_type_enum = Enum(
    ProjectLogType, name="project_log_type", native_enum=False, create_constraint=True
)
memory_source_enum = Enum(
    MemorySource, name="memory_source", native_enum=False, create_constraint=True
)
memory_entity_type_enum = Enum(
    MemoryEntityType, name="memory_entity_type", native_enum=False, create_constraint=True
)
meeting_status_enum = Enum(
    MeetingStatus, name="meeting_status", native_enum=False, create_constraint=True
)
action_item_status_enum = Enum(
    ActionItemStatus, name="action_item_status", native_enum=False, create_constraint=True
)
decision_status_enum = Enum(
    DecisionStatus, name="decision_status", native_enum=False, create_constraint=True
)


class ProjectLogEntry(UUIDTimestampMixin, Base):
    __tablename__ = "project_log_entries"
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_project_log_entries_project_id"),
        Index("ix_project_log_project_created", "project_id", "created_at"),
        Index("ix_project_log_project_type", "project_id", "type"),
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[ProjectLogType] = mapped_column(project_log_type_enum, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[MemorySource] = mapped_column(memory_source_enum, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    links: Mapped[list["ProjectLogLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class ProjectLogLink(Base):
    __tablename__ = "project_log_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "log_entry_id"],
            ["project_log_entries.project_id", "project_log_entries.id"],
            ondelete="CASCADE",
            name="fk_project_log_links_project_entry",
        ),
        Index("ix_project_log_links_entity", "project_id", "entity_type", "entity_id"),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    log_entry_id: Mapped[UUID] = mapped_column(primary_key=True)
    entity_type: Mapped[MemoryEntityType] = mapped_column(memory_entity_type_enum, primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(primary_key=True)


class Meeting(UUIDTimestampMixin, Base):
    __tablename__ = "meetings"
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_meetings_project_id"),
        Index("ix_meetings_project_schedule", "project_id", "scheduled_at"),
        Index("ix_meetings_project_status", "project_id", "status"),
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agenda: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(
        meeting_status_enum, default=MeetingStatus.PLANNED, nullable=False
    )
    participants: Mapped[list["MeetingParticipant"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    action_items: Mapped[list["MeetingActionItem"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            ondelete="CASCADE",
            name="fk_meeting_participants_project_meeting",
        ),
        ForeignKeyConstraint(
            ["project_id", "project_member_id"],
            ["project_members.project_id", "project_members.id"],
            ondelete="RESTRICT",
            name="fk_meeting_participants_project_member",
        ),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    meeting_id: Mapped[UUID] = mapped_column(primary_key=True)
    project_member_id: Mapped[UUID] = mapped_column(primary_key=True)


class MeetingActionItem(UUIDTimestampMixin, Base):
    __tablename__ = "meeting_action_items"
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_meeting_action_items_project_id"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            ondelete="CASCADE",
            name="fk_meeting_action_items_project_meeting",
        ),
        ForeignKeyConstraint(
            ["project_id", "owner_member_id"],
            ["project_members.project_id", "project_members.id"],
            ondelete="RESTRICT",
            name="fk_meeting_action_items_project_owner",
        ),
        ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="RESTRICT",
            name="fk_meeting_action_items_project_task",
        ),
        Index("ix_action_items_project_status", "project_id", "status"),
        Index("ix_action_items_project_due", "project_id", "due_date"),
    )
    project_id: Mapped[UUID] = mapped_column(nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_member_id: Mapped[UUID | None] = mapped_column(nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ActionItemStatus] = mapped_column(
        action_item_status_enum, default=ActionItemStatus.PROPOSED, nullable=False
    )
    task_id: Mapped[UUID | None] = mapped_column(nullable=True)


class Decision(UUIDTimestampMixin, Base):
    __tablename__ = "decisions"
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_decisions_project_id"),
        ForeignKeyConstraint(
            ["project_id", "meeting_id"],
            ["meetings.project_id", "meetings.id"],
            ondelete="RESTRICT",
            name="fk_decisions_project_meeting",
        ),
        ForeignKeyConstraint(
            ["project_id", "decision_maker_member_id"],
            ["project_members.project_id", "project_members.id"],
            ondelete="RESTRICT",
            name="fk_decisions_project_maker",
        ),
        Index("ix_decisions_project_date", "project_id", "decision_date"),
        Index("ix_decisions_project_status", "project_id", "status"),
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    meeting_id: Mapped[UUID | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    decision_date: Mapped[date] = mapped_column(Date, nullable=False)
    decision_maker_member_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternatives: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_option: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DecisionStatus] = mapped_column(
        decision_status_enum, default=DecisionStatus.PROPOSED, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    links: Mapped[list["DecisionLink"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class DecisionLink(Base):
    __tablename__ = "decision_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "decision_id"],
            ["decisions.project_id", "decisions.id"],
            ondelete="CASCADE",
            name="fk_decision_links_project_decision",
        ),
        Index("ix_decision_links_entity", "project_id", "entity_type", "entity_id"),
    )
    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    decision_id: Mapped[UUID] = mapped_column(primary_key=True)
    entity_type: Mapped[MemoryEntityType] = mapped_column(memory_entity_type_enum, primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(primary_key=True)
