from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics.control import RiskSeverity
from app.models.control import (
    ChangeRequest,
    ChangeRequestIssueLink,
    ChangeRequestMilestoneLink,
    ChangeRequestRiskLink,
    ChangeRequestTaskLink,
    ChangeStatus,
    ControlPriority,
    Issue,
    IssueMilestoneLink,
    IssueStatus,
    IssueTaskLink,
    Risk,
    RiskMilestoneLink,
    RiskStatus,
    RiskTaskLink,
)
from app.models.milestone import Milestone
from app.models.people import ProjectMember
from app.models.project import Project
from app.models.task import Task
from app.schemas.control import ChangeSort, IssueSort, RiskSort, SortOrder
from app.services.authorization import accessible_project_ids


class ControlRepository:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id

    async def get_project(self, project_id: UUID) -> Project | None:
        return (
            await self.session.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.id.in_(accessible_project_ids(self.owner_user_id)),
                )
            )
        ).scalar_one_or_none()

    async def get_risk(self, project_id: UUID, risk_id: UUID) -> Risk | None:
        return (
            await self.session.execute(
                select(Risk)
                .join(Project, Project.id == Risk.project_id)
                .options(selectinload(Risk.task_links), selectinload(Risk.milestone_links))
                .where(
                    Risk.id == risk_id,
                    Risk.project_id == project_id,
                    Project.id.in_(accessible_project_ids(self.owner_user_id)),
                )
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def list_risks(
        self,
        project_id: UUID,
        *,
        search: str | None,
        status: RiskStatus | None,
        severity: RiskSeverity | None,
        sort_by: RiskSort,
        sort_order: SortOrder,
    ) -> tuple[list[Risk], int]:
        score = Risk.probability * Risk.impact
        filters = [Risk.project_id == project_id]
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(Risk.title.ilike(term), Risk.description.ilike(term), Risk.category.ilike(term))
            )
        if status:
            filters.append(Risk.status == status)
        if severity == RiskSeverity.LOW:
            filters.append(score <= 4)
        elif severity == RiskSeverity.MEDIUM:
            filters.extend((score >= 5, score <= 9))
        elif severity == RiskSeverity.HIGH:
            filters.extend((score >= 10, score <= 16))
        elif severity == RiskSeverity.CRITICAL:
            filters.append(score >= 17)
        total = int(
            (await self.session.execute(select(func.count(Risk.id)).where(*filters))).scalar_one()
        )
        column = {
            RiskSort.UPDATED_AT: Risk.updated_at,
            RiskSort.TITLE: Risk.title,
            RiskSort.SCORE: score,
            RiskSort.PROBABILITY: Risk.probability,
            RiskSort.IMPACT: Risk.impact,
            RiskSort.REVIEW_DATE: Risk.review_date,
        }[sort_by]
        ordering = column.asc() if sort_order == SortOrder.ASC else column.desc()
        result = await self.session.execute(
            select(Risk)
            .options(selectinload(Risk.task_links), selectinload(Risk.milestone_links))
            .where(*filters)
            .order_by(ordering, Risk.id)
        )
        return list(result.scalars()), total

    async def get_issue(self, project_id: UUID, issue_id: UUID) -> Issue | None:
        return (
            await self.session.execute(
                select(Issue)
                .join(Project, Project.id == Issue.project_id)
                .options(selectinload(Issue.task_links), selectinload(Issue.milestone_links))
                .where(
                    Issue.id == issue_id,
                    Issue.project_id == project_id,
                    Project.id.in_(accessible_project_ids(self.owner_user_id)),
                )
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def list_issues(
        self,
        project_id: UUID,
        *,
        search: str | None,
        status: IssueStatus | None,
        priority: ControlPriority | None,
        sort_by: IssueSort,
        sort_order: SortOrder,
    ) -> tuple[list[Issue], int]:
        filters = [Issue.project_id == project_id]
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Issue.title.ilike(term),
                    Issue.description.ilike(term),
                    Issue.category.ilike(term),
                )
            )
        if status:
            filters.append(Issue.status == status)
        if priority:
            filters.append(Issue.priority == priority)
        total = int(
            (await self.session.execute(select(func.count(Issue.id)).where(*filters))).scalar_one()
        )
        column = {
            IssueSort.UPDATED_AT: Issue.updated_at,
            IssueSort.TITLE: Issue.title,
            IssueSort.IDENTIFIED_DATE: Issue.identified_date,
            IssueSort.PRIORITY: Issue.priority,
            IssueSort.STATUS: Issue.status,
        }[sort_by]
        ordering = column.asc() if sort_order == SortOrder.ASC else column.desc()
        result = await self.session.execute(
            select(Issue)
            .options(selectinload(Issue.task_links), selectinload(Issue.milestone_links))
            .where(*filters)
            .order_by(ordering, Issue.id)
        )
        return list(result.scalars()), total

    async def get_change(self, project_id: UUID, change_id: UUID) -> ChangeRequest | None:
        return (
            await self.session.execute(
                select(ChangeRequest)
                .join(Project, Project.id == ChangeRequest.project_id)
                .options(
                    selectinload(ChangeRequest.task_links),
                    selectinload(ChangeRequest.milestone_links),
                    selectinload(ChangeRequest.issue_links),
                    selectinload(ChangeRequest.risk_links),
                )
                .where(
                    ChangeRequest.id == change_id,
                    ChangeRequest.project_id == project_id,
                    Project.id.in_(accessible_project_ids(self.owner_user_id)),
                )
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def list_changes(
        self,
        project_id: UUID,
        *,
        search: str | None,
        status: ChangeStatus | None,
        sort_by: ChangeSort,
        sort_order: SortOrder,
    ) -> tuple[list[ChangeRequest], int]:
        filters = [ChangeRequest.project_id == project_id]
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    ChangeRequest.title.ilike(term),
                    ChangeRequest.description.ilike(term),
                    ChangeRequest.reason.ilike(term),
                    ChangeRequest.requested_by.ilike(term),
                )
            )
        if status:
            filters.append(ChangeRequest.status == status)
        total = int(
            (
                await self.session.execute(select(func.count(ChangeRequest.id)).where(*filters))
            ).scalar_one()
        )
        column = {
            ChangeSort.UPDATED_AT: ChangeRequest.updated_at,
            ChangeSort.TITLE: ChangeRequest.title,
            ChangeSort.REQUESTED_DATE: ChangeRequest.requested_date,
            ChangeSort.STATUS: ChangeRequest.status,
        }[sort_by]
        ordering = column.asc() if sort_order == SortOrder.ASC else column.desc()
        result = await self.session.execute(
            select(ChangeRequest)
            .options(
                selectinload(ChangeRequest.task_links),
                selectinload(ChangeRequest.milestone_links),
                selectinload(ChangeRequest.issue_links),
                selectinload(ChangeRequest.risk_links),
            )
            .where(*filters)
            .order_by(ordering, ChangeRequest.id)
        )
        return list(result.scalars()), total

    async def member_exists(self, project_id: UUID, member_id: UUID) -> bool:
        return bool(
            (
                await self.session.execute(
                    select(func.count(ProjectMember.id)).where(
                        ProjectMember.project_id == project_id, ProjectMember.id == member_id
                    )
                )
            ).scalar_one()
        )

    async def task_ids_exist(self, project_id: UUID, ids: list[UUID]) -> bool:
        if not ids:
            return True
        count = (
            await self.session.execute(
                select(func.count(Task.id)).where(Task.project_id == project_id, Task.id.in_(ids))
            )
        ).scalar_one()
        return int(count) == len(ids)

    async def milestone_ids_exist(self, project_id: UUID, ids: list[UUID]) -> bool:
        if not ids:
            return True
        count = (
            await self.session.execute(
                select(func.count(Milestone.id)).where(
                    Milestone.project_id == project_id, Milestone.id.in_(ids)
                )
            )
        ).scalar_one()
        return int(count) == len(ids)

    async def issue_ids_exist(self, project_id: UUID, ids: list[UUID]) -> bool:
        if not ids:
            return True
        count = (
            await self.session.execute(
                select(func.count(Issue.id)).where(
                    Issue.project_id == project_id, Issue.id.in_(ids)
                )
            )
        ).scalar_one()
        return int(count) == len(ids)

    async def risk_ids_exist(self, project_id: UUID, ids: list[UUID]) -> bool:
        if not ids:
            return True
        count = (
            await self.session.execute(
                select(func.count(Risk.id)).where(Risk.project_id == project_id, Risk.id.in_(ids))
            )
        ).scalar_one()
        return int(count) == len(ids)

    async def set_risk_links(
        self, project_id: UUID, risk_id: UUID, task_ids: list[UUID], milestone_ids: list[UUID]
    ) -> None:
        await self.session.execute(
            delete(RiskTaskLink).where(
                RiskTaskLink.project_id == project_id, RiskTaskLink.risk_id == risk_id
            )
        )
        await self.session.execute(
            delete(RiskMilestoneLink).where(
                RiskMilestoneLink.project_id == project_id,
                RiskMilestoneLink.risk_id == risk_id,
            )
        )
        self.session.add_all(
            [
                RiskTaskLink(project_id=project_id, risk_id=risk_id, task_id=value)
                for value in task_ids
            ]
            + [
                RiskMilestoneLink(project_id=project_id, risk_id=risk_id, milestone_id=value)
                for value in milestone_ids
            ]
        )

    async def set_issue_links(
        self, project_id: UUID, issue_id: UUID, task_ids: list[UUID], milestone_ids: list[UUID]
    ) -> None:
        await self.session.execute(
            delete(IssueTaskLink).where(
                IssueTaskLink.project_id == project_id, IssueTaskLink.issue_id == issue_id
            )
        )
        await self.session.execute(
            delete(IssueMilestoneLink).where(
                IssueMilestoneLink.project_id == project_id,
                IssueMilestoneLink.issue_id == issue_id,
            )
        )
        self.session.add_all(
            [
                IssueTaskLink(project_id=project_id, issue_id=issue_id, task_id=value)
                for value in task_ids
            ]
            + [
                IssueMilestoneLink(project_id=project_id, issue_id=issue_id, milestone_id=value)
                for value in milestone_ids
            ]
        )

    async def set_change_links(
        self,
        project_id: UUID,
        change_id: UUID,
        *,
        task_ids: list[UUID],
        milestone_ids: list[UUID],
        issue_ids: list[UUID],
        risk_ids: list[UUID],
    ) -> None:
        for model in (
            ChangeRequestTaskLink,
            ChangeRequestMilestoneLink,
            ChangeRequestIssueLink,
            ChangeRequestRiskLink,
        ):
            await self.session.execute(
                delete(model).where(
                    model.project_id == project_id, model.change_request_id == change_id
                )
            )
        self.session.add_all(
            [
                ChangeRequestTaskLink(
                    project_id=project_id, change_request_id=change_id, task_id=value
                )
                for value in task_ids
            ]
            + [
                ChangeRequestMilestoneLink(
                    project_id=project_id, change_request_id=change_id, milestone_id=value
                )
                for value in milestone_ids
            ]
            + [
                ChangeRequestIssueLink(
                    project_id=project_id, change_request_id=change_id, issue_id=value
                )
                for value in issue_ids
            ]
            + [
                ChangeRequestRiskLink(
                    project_id=project_id, change_request_id=change_id, risk_id=value
                )
                for value in risk_ids
            ]
        )

    async def summary_counts(self, project_id: UUID) -> tuple[int, int, int, int, int]:
        score = Risk.probability * Risk.impact
        open_risks = int(
            (
                await self.session.execute(
                    select(func.count(Risk.id)).where(
                        Risk.project_id == project_id, Risk.status != RiskStatus.CLOSED
                    )
                )
            ).scalar_one()
        )
        severe_risks = int(
            (
                await self.session.execute(
                    select(func.count(Risk.id)).where(
                        Risk.project_id == project_id,
                        Risk.status != RiskStatus.CLOSED,
                        score >= 10,
                    )
                )
            ).scalar_one()
        )
        open_issue_filter = (
            Issue.project_id == project_id,
            Issue.status.not_in((IssueStatus.RESOLVED, IssueStatus.CLOSED)),
        )
        open_issues = int(
            (
                await self.session.execute(select(func.count(Issue.id)).where(*open_issue_filter))
            ).scalar_one()
        )
        critical_issues = int(
            (
                await self.session.execute(
                    select(func.count(Issue.id)).where(
                        *open_issue_filter, Issue.priority == ControlPriority.CRITICAL
                    )
                )
            ).scalar_one()
        )
        pending_changes = int(
            (
                await self.session.execute(
                    select(func.count(ChangeRequest.id)).where(
                        ChangeRequest.project_id == project_id,
                        ChangeRequest.status == ChangeStatus.PENDING,
                    )
                )
            ).scalar_one()
        )
        return open_risks, severe_risks, open_issues, critical_issues, pending_changes
