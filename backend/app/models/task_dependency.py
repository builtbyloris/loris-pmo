from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDTimestampMixin


class DependencyType(StrEnum):
    BLOCKS = "BLOCKS"
    DEPENDS_ON = "DEPENDS_ON"
    RELATED_TO = "RELATED_TO"


dependency_type_enum = Enum(
    DependencyType,
    name="task_dependency_type",
    native_enum=False,
    create_constraint=True,
)


class TaskDependency(UUIDTimestampMixin, Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        CheckConstraint("source_task_id <> target_task_id", name="task_dependency_not_self"),
        UniqueConstraint(
            "project_id",
            "source_task_id",
            "target_task_id",
            "dependency_type",
            name="uq_task_dependencies_relation",
        ),
        ForeignKeyConstraint(
            ["project_id", "source_task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="CASCADE",
            name="fk_task_dependencies_project_source",
        ),
        ForeignKeyConstraint(
            ["project_id", "target_task_id"],
            ["tasks.project_id", "tasks.id"],
            ondelete="CASCADE",
            name="fk_task_dependencies_project_target",
        ),
        Index("ix_task_dependencies_source", "project_id", "source_task_id"),
        Index("ix_task_dependencies_target", "project_id", "target_task_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    source_task_id: Mapped[UUID] = mapped_column(nullable=False)
    target_task_id: Mapped[UUID] = mapped_column(nullable=False)
    dependency_type: Mapped[DependencyType] = mapped_column(dependency_type_enum, nullable=False)
