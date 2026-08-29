from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.control import ChangeRequest, Issue, Risk
from app.models.intelligence import Alert, AlertSeverity, AlertStatus, HealthSnapshot
from app.models.memory import Decision, MeetingActionItem, ProjectLogEntry
from app.models.milestone import Milestone
from app.models.objective import Objective
from app.models.project import Project
from app.models.success_criterion import SuccessCriterion
from app.models.task import Task


class IntelligenceRepository:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id

    async def project(self, project_id: UUID) -> Project | None:
        return (
            await self.session.execute(
                select(Project).where(
                    Project.id == project_id, Project.owner_user_id == self.owner_user_id
                )
            )
        ).scalar_one_or_none()

    async def portfolio_projects(self) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.owner_user_id == self.owner_user_id, Project.archived_at.is_(None))
            .order_by(Project.name)
        )
        return list(result.scalars())

    async def project_facts(self, project_id: UUID) -> dict[str, list]:
        models = {
            "tasks": Task,
            "milestones": Milestone,
            "objectives": Objective,
            "criteria": SuccessCriterion,
            "risks": Risk,
            "issues": Issue,
            "changes": ChangeRequest,
            "actions": MeetingActionItem,
            "decisions": Decision,
            "logs": ProjectLogEntry,
        }
        rows: dict[str, list] = {}
        for key, model in models.items():
            query = select(model).where(model.project_id == project_id)
            if model is Task:
                query = query.where(Task.archived_at.is_(None))
            rows[key] = list((await self.session.execute(query)).scalars())
        return rows

    async def alerts(
        self,
        project_id: UUID,
        *,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
    ) -> list[Alert]:
        query = select(Alert).where(Alert.project_id == project_id)
        if status:
            query = query.where(Alert.status == status)
        if severity:
            query = query.where(Alert.severity == severity)
        result = await self.session.execute(
            query.order_by(Alert.severity.desc(), Alert.last_detected_at.desc())
        )
        return list(result.scalars())

    async def alert(self, project_id: UUID, alert_id: UUID) -> Alert | None:
        return (
            await self.session.execute(
                select(Alert).where(Alert.project_id == project_id, Alert.id == alert_id)
            )
        ).scalar_one_or_none()

    async def latest_snapshot(self, project_id: UUID) -> HealthSnapshot | None:
        return (
            await self.session.execute(
                select(HealthSnapshot)
                .where(HealthSnapshot.project_id == project_id)
                .order_by(HealthSnapshot.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def history(self, project_id: UUID, limit: int = 20) -> list[HealthSnapshot]:
        result = await self.session.execute(
            select(HealthSnapshot)
            .where(HealthSnapshot.project_id == project_id)
            .order_by(HealthSnapshot.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())
