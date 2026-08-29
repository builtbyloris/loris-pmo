from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.control import risk_score, risk_severity
from app.core.errors import AppError
from app.models.control import ChangeRequest, ChangeStatus, Issue, IssueStatus, Risk, RiskStatus
from app.models.memory import MemoryEntityType, ProjectLogType
from app.models.project import Project
from app.repositories.control import ControlRepository
from app.schemas.control import (
    ChangeCreate,
    ChangeDecision,
    ChangeList,
    ChangeRead,
    ChangeUpdate,
    ControlSummary,
    IssueCreate,
    IssueList,
    IssueRead,
    IssueResolution,
    IssueUpdate,
    RiskCreate,
    RiskList,
    RiskRead,
    RiskUpdate,
)
from app.services.audit import AuditService
from app.services.memory import MemoryService

ISSUE_TRANSITIONS: dict[IssueStatus, set[IssueStatus]] = {
    IssueStatus.OPEN: {
        IssueStatus.IN_ANALYSIS,
        IssueStatus.ACTION_PLANNED,
        IssueStatus.IN_PROGRESS,
        IssueStatus.RESOLVED,
        IssueStatus.CLOSED,
    },
    IssueStatus.IN_ANALYSIS: {
        IssueStatus.ACTION_PLANNED,
        IssueStatus.IN_PROGRESS,
        IssueStatus.RESOLVED,
        IssueStatus.CLOSED,
    },
    IssueStatus.ACTION_PLANNED: {
        IssueStatus.IN_PROGRESS,
        IssueStatus.RESOLVED,
        IssueStatus.CLOSED,
    },
    IssueStatus.IN_PROGRESS: {IssueStatus.RESOLVED, IssueStatus.CLOSED},
    IssueStatus.RESOLVED: {IssueStatus.CLOSED},
    IssueStatus.CLOSED: set(),
}


class ControlService:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.repository = ControlRepository(session, owner_user_id)
        self.audit = AuditService(session, owner_user_id)

    async def _project_or_404(self, project_id: UUID) -> Project:
        project = await self.repository.get_project(project_id)
        if project is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        return project

    @staticmethod
    def _ensure_mutable(project: Project) -> None:
        if project.archived_at is not None:
            raise AppError(
                code="project_archived", message="Archived projects are read-only.", status_code=409
            )

    async def _risk_or_404(self, project_id: UUID, risk_id: UUID) -> Risk:
        risk = await self.repository.get_risk(project_id, risk_id)
        if risk is None:
            raise AppError(code="risk_not_found", message="Risk not found.", status_code=404)
        return risk

    async def _issue_or_404(self, project_id: UUID, issue_id: UUID) -> Issue:
        issue = await self.repository.get_issue(project_id, issue_id)
        if issue is None:
            raise AppError(code="issue_not_found", message="Issue not found.", status_code=404)
        return issue

    async def _change_or_404(self, project_id: UUID, change_id: UUID) -> ChangeRequest:
        change = await self.repository.get_change(project_id, change_id)
        if change is None:
            raise AppError(
                code="change_request_not_found",
                message="Change request not found.",
                status_code=404,
            )
        return change

    async def _validate_owner(self, project_id: UUID, member_id: UUID | None) -> None:
        if member_id and not await self.repository.member_exists(project_id, member_id):
            raise AppError(
                code="invalid_owner_member",
                message="The owner must be a member of this project.",
                status_code=422,
            )

    async def _validate_work_links(
        self, project_id: UUID, task_ids: list[UUID], milestone_ids: list[UUID]
    ) -> None:
        if not await self.repository.task_ids_exist(project_id, task_ids):
            raise AppError(
                code="invalid_related_task",
                message="Every linked task must belong to this project.",
                status_code=422,
            )
        if not await self.repository.milestone_ids_exist(project_id, milestone_ids):
            raise AppError(
                code="invalid_related_milestone",
                message="Every linked milestone must belong to this project.",
                status_code=422,
            )

    async def _validate_change_links(
        self,
        project_id: UUID,
        *,
        task_ids: list[UUID],
        milestone_ids: list[UUID],
        issue_ids: list[UUID],
        risk_ids: list[UUID],
    ) -> None:
        await self._validate_work_links(project_id, task_ids, milestone_ids)
        if not await self.repository.issue_ids_exist(project_id, issue_ids):
            raise AppError(
                code="invalid_related_issue",
                message="Every linked issue must belong to this project.",
                status_code=422,
            )
        if not await self.repository.risk_ids_exist(project_id, risk_ids):
            raise AppError(
                code="invalid_related_risk",
                message="Every linked risk must belong to this project.",
                status_code=422,
            )

    @staticmethod
    def _risk_read(risk: Risk) -> RiskRead:
        score = risk_score(risk.probability, risk.impact)
        return RiskRead(
            id=risk.id,
            project_id=risk.project_id,
            title=risk.title,
            description=risk.description,
            category=risk.category,
            probability=risk.probability,
            impact=risk.impact,
            risk_score=score,
            severity=risk_severity(score),
            owner_member_id=risk.owner_member_id,
            mitigation=risk.mitigation,
            contingency=risk.contingency,
            status=risk.status,
            identified_date=risk.identified_date,
            review_date=risk.review_date,
            notes=risk.notes,
            task_ids=[link.task_id for link in risk.task_links],
            milestone_ids=[link.milestone_id for link in risk.milestone_links],
            created_at=risk.created_at,
            updated_at=risk.updated_at,
        )

    @staticmethod
    def _issue_read(issue: Issue) -> IssueRead:
        return IssueRead(
            id=issue.id,
            project_id=issue.project_id,
            title=issue.title,
            description=issue.description,
            category=issue.category,
            priority=issue.priority,
            status=issue.status,
            owner_member_id=issue.owner_member_id,
            identified_date=issue.identified_date,
            schedule_impact=issue.schedule_impact,
            budget_impact=issue.budget_impact,
            scope_impact=issue.scope_impact,
            quality_impact=issue.quality_impact,
            estimated_delay_days=issue.estimated_delay_days,
            estimated_cost=issue.estimated_cost,
            actual_delay_days=issue.actual_delay_days,
            actual_cost=issue.actual_cost,
            resolution=issue.resolution,
            notes=issue.notes,
            resolved_at=issue.resolved_at,
            task_ids=[link.task_id for link in issue.task_links],
            milestone_ids=[link.milestone_id for link in issue.milestone_links],
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )

    @staticmethod
    def _change_read(change: ChangeRequest) -> ChangeRead:
        return ChangeRead(
            id=change.id,
            project_id=change.project_id,
            title=change.title,
            description=change.description,
            reason=change.reason,
            requested_by=change.requested_by,
            requested_date=change.requested_date,
            status=change.status,
            scope_impact=change.scope_impact,
            schedule_impact=change.schedule_impact,
            budget_impact=change.budget_impact,
            resource_impact=change.resource_impact,
            estimated_delay_days=change.estimated_delay_days,
            estimated_cost=change.estimated_cost,
            decision=change.decision,
            decision_date=change.decision_date,
            notes=change.notes,
            task_ids=[link.task_id for link in change.task_links],
            milestone_ids=[link.milestone_id for link in change.milestone_links],
            issue_ids=[link.issue_id for link in change.issue_links],
            risk_ids=[link.risk_id for link in change.risk_links],
            created_at=change.created_at,
            updated_at=change.updated_at,
        )

    async def list_risks(self, project_id: UUID, **filters) -> RiskList:
        await self._project_or_404(project_id)
        risks, total = await self.repository.list_risks(project_id, **filters)
        return RiskList(items=[self._risk_read(item) for item in risks], total=total)

    async def get_risk(self, project_id: UUID, risk_id: UUID) -> RiskRead:
        await self._project_or_404(project_id)
        return self._risk_read(await self._risk_or_404(project_id, risk_id))

    async def create_risk(self, project_id: UUID, data: RiskCreate) -> RiskRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        await self._validate_owner(project_id, data.owner_member_id)
        await self._validate_work_links(project_id, data.task_ids, data.milestone_ids)
        values = data.model_dump(exclude={"task_ids", "milestone_ids"})
        risk = Risk(project_id=project_id, **values)
        self.session.add(risk)
        await self.session.flush()
        await self.repository.set_risk_links(project_id, risk.id, data.task_ids, data.milestone_ids)
        score = risk_score(risk.probability, risk.impact)
        self.audit.record(
            project_id=project_id,
            action="risk.created",
            entity_type="risk",
            entity_id=risk.id,
            changes={"title": risk.title, "score": score, "severity": risk_severity(score).value},
        )
        await self.session.commit()
        return self._risk_read(await self._risk_or_404(project_id, risk.id))

    async def update_risk(self, project_id: UUID, risk_id: UUID, data: RiskUpdate) -> RiskRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        risk = await self._risk_or_404(project_id, risk_id)
        if risk.status == RiskStatus.CLOSED:
            raise AppError(
                code="risk_closed", message="Closed risks are read-only.", status_code=409
            )
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return self._risk_read(risk)
        task_ids = changes.pop("task_ids", [link.task_id for link in risk.task_links])
        milestone_ids = changes.pop(
            "milestone_ids", [link.milestone_id for link in risk.milestone_links]
        )
        await self._validate_owner(project_id, changes.get("owner_member_id", risk.owner_member_id))
        await self._validate_work_links(project_id, task_ids, milestone_ids)
        identified = changes.get("identified_date", risk.identified_date)
        review = changes.get("review_date", risk.review_date)
        if review and review < identified:
            raise AppError(
                code="invalid_risk_dates",
                message="Review date must not precede identified date.",
                status_code=422,
            )
        old_status = risk.status
        old_score = risk_score(risk.probability, risk.impact)
        before = {key: str(getattr(risk, key)) for key in changes}
        for key, value in changes.items():
            setattr(risk, key, value)
        await self.repository.set_risk_links(project_id, risk.id, task_ids, milestone_ids)
        new_score = risk_score(risk.probability, risk.impact)
        self.audit.record(
            project_id=project_id,
            action="risk.updated",
            entity_type="risk",
            entity_id=risk.id,
            changes={"before": before, "fields": list(changes)},
        )
        if risk_severity(old_score) != risk_severity(new_score):
            self.audit.record(
                project_id=project_id,
                action="risk.severity_changed",
                entity_type="risk",
                entity_id=risk.id,
                changes={
                    "from": risk_severity(old_score).value,
                    "to": risk_severity(new_score).value,
                    "score": new_score,
                },
            )
        if risk.status != old_status:
            self.audit.record(
                project_id=project_id,
                action="risk.status_changed",
                entity_type="risk",
                entity_id=risk.id,
                changes={"from": old_status.value, "to": risk.status.value},
            )
            if risk.status == RiskStatus.CLOSED:
                self.audit.record(
                    project_id=project_id,
                    action="risk.closed",
                    entity_type="risk",
                    entity_id=risk.id,
                )
                MemoryService.record_system_log(
                    self.session,
                    actor_user_id=self.owner_user_id,
                    project_id=project_id,
                    entry_type=ProjectLogType.RISK_UPDATE,
                    title=f"Risk closed: {risk.title}",
                    description=risk.notes,
                    entity_type=MemoryEntityType.RISK,
                    entity_id=risk.id,
                )
        await self.session.commit()
        return self._risk_read(await self._risk_or_404(project_id, risk.id))

    async def close_risk(self, project_id: UUID, risk_id: UUID) -> RiskRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        risk = await self._risk_or_404(project_id, risk_id)
        if risk.status == RiskStatus.CLOSED:
            return self._risk_read(risk)
        return await self.update_risk(project_id, risk_id, RiskUpdate(status=RiskStatus.CLOSED))

    async def list_issues(self, project_id: UUID, **filters) -> IssueList:
        await self._project_or_404(project_id)
        issues, total = await self.repository.list_issues(project_id, **filters)
        return IssueList(items=[self._issue_read(item) for item in issues], total=total)

    async def get_issue(self, project_id: UUID, issue_id: UUID) -> IssueRead:
        await self._project_or_404(project_id)
        return self._issue_read(await self._issue_or_404(project_id, issue_id))

    async def create_issue(self, project_id: UUID, data: IssueCreate) -> IssueRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        await self._validate_owner(project_id, data.owner_member_id)
        await self._validate_work_links(project_id, data.task_ids, data.milestone_ids)
        issue = Issue(
            project_id=project_id,
            **data.model_dump(exclude={"task_ids", "milestone_ids"}),
        )
        self.session.add(issue)
        await self.session.flush()
        await self.repository.set_issue_links(
            project_id, issue.id, data.task_ids, data.milestone_ids
        )
        self.audit.record(
            project_id=project_id,
            action="issue.created",
            entity_type="issue",
            entity_id=issue.id,
            changes={"title": issue.title, "priority": issue.priority.value},
        )
        await self.session.commit()
        return self._issue_read(await self._issue_or_404(project_id, issue.id))

    async def update_issue(self, project_id: UUID, issue_id: UUID, data: IssueUpdate) -> IssueRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        issue = await self._issue_or_404(project_id, issue_id)
        if issue.status == IssueStatus.CLOSED:
            raise AppError(
                code="issue_closed", message="Closed issues are read-only.", status_code=409
            )
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return self._issue_read(issue)
        task_ids = changes.pop("task_ids", [link.task_id for link in issue.task_links])
        milestone_ids = changes.pop(
            "milestone_ids", [link.milestone_id for link in issue.milestone_links]
        )
        await self._validate_owner(
            project_id, changes.get("owner_member_id", issue.owner_member_id)
        )
        await self._validate_work_links(project_id, task_ids, milestone_ids)
        old_status = issue.status
        new_status = changes.get("status", old_status)
        if new_status != old_status and new_status not in ISSUE_TRANSITIONS[old_status]:
            raise AppError(
                code="invalid_issue_transition",
                message=f"Issue cannot move from {old_status.value} to {new_status.value}.",
                status_code=409,
            )
        resolution = changes.get("resolution", issue.resolution)
        if new_status in (IssueStatus.RESOLVED, IssueStatus.CLOSED) and not resolution:
            raise AppError(
                code="issue_resolution_required",
                message="A resolution is required before resolving or closing an issue.",
                status_code=422,
            )
        before = {key: str(getattr(issue, key)) for key in changes}
        for key, value in changes.items():
            setattr(issue, key, value)
        if new_status in (IssueStatus.RESOLVED, IssueStatus.CLOSED) and issue.resolved_at is None:
            issue.resolved_at = datetime.now(UTC)
        await self.repository.set_issue_links(project_id, issue.id, task_ids, milestone_ids)
        self.audit.record(
            project_id=project_id,
            action="issue.updated",
            entity_type="issue",
            entity_id=issue.id,
            changes={"before": before, "fields": list(changes)},
        )
        if issue.status != old_status:
            self.audit.record(
                project_id=project_id,
                action="issue.status_changed",
                entity_type="issue",
                entity_id=issue.id,
                changes={"from": old_status.value, "to": issue.status.value},
            )
            if issue.status == IssueStatus.RESOLVED:
                self.audit.record(
                    project_id=project_id,
                    action="issue.resolved",
                    entity_type="issue",
                    entity_id=issue.id,
                )
                MemoryService.record_system_log(
                    self.session,
                    actor_user_id=self.owner_user_id,
                    project_id=project_id,
                    entry_type=ProjectLogType.ISSUE,
                    title=f"Issue resolved: {issue.title}",
                    description=issue.resolution,
                    entity_type=MemoryEntityType.ISSUE,
                    entity_id=issue.id,
                )
            if issue.status == IssueStatus.CLOSED:
                self.audit.record(
                    project_id=project_id,
                    action="issue.closed",
                    entity_type="issue",
                    entity_id=issue.id,
                )
        await self.session.commit()
        return self._issue_read(await self._issue_or_404(project_id, issue.id))

    async def resolve_issue(
        self, project_id: UUID, issue_id: UUID, data: IssueResolution
    ) -> IssueRead:
        return await self.update_issue(
            project_id,
            issue_id,
            IssueUpdate(status=IssueStatus.RESOLVED, **data.model_dump()),
        )

    async def close_issue(self, project_id: UUID, issue_id: UUID) -> IssueRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        issue = await self._issue_or_404(project_id, issue_id)
        if issue.status == IssueStatus.CLOSED:
            return self._issue_read(issue)
        return await self.update_issue(project_id, issue_id, IssueUpdate(status=IssueStatus.CLOSED))

    async def list_changes(self, project_id: UUID, **filters) -> ChangeList:
        await self._project_or_404(project_id)
        changes, total = await self.repository.list_changes(project_id, **filters)
        return ChangeList(items=[self._change_read(item) for item in changes], total=total)

    async def get_change(self, project_id: UUID, change_id: UUID) -> ChangeRead:
        await self._project_or_404(project_id)
        return self._change_read(await self._change_or_404(project_id, change_id))

    async def create_change(self, project_id: UUID, data: ChangeCreate) -> ChangeRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        await self._validate_change_links(
            project_id,
            task_ids=data.task_ids,
            milestone_ids=data.milestone_ids,
            issue_ids=data.issue_ids,
            risk_ids=data.risk_ids,
        )
        change = ChangeRequest(
            project_id=project_id,
            **data.model_dump(exclude={"task_ids", "milestone_ids", "issue_ids", "risk_ids"}),
        )
        self.session.add(change)
        await self.session.flush()
        await self.repository.set_change_links(
            project_id,
            change.id,
            task_ids=data.task_ids,
            milestone_ids=data.milestone_ids,
            issue_ids=data.issue_ids,
            risk_ids=data.risk_ids,
        )
        self.audit.record(
            project_id=project_id,
            action="change_request.created",
            entity_type="change_request",
            entity_id=change.id,
            changes={"title": change.title, "status": change.status.value},
        )
        await self.session.commit()
        return self._change_read(await self._change_or_404(project_id, change.id))

    async def update_change(
        self, project_id: UUID, change_id: UUID, data: ChangeUpdate
    ) -> ChangeRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        change = await self._change_or_404(project_id, change_id)
        if change.status not in (ChangeStatus.DRAFT, ChangeStatus.PENDING):
            raise AppError(
                code="change_request_locked",
                message="Decided change requests are read-only.",
                status_code=409,
            )
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return self._change_read(change)
        task_ids = changes.pop("task_ids", [link.task_id for link in change.task_links])
        milestone_ids = changes.pop(
            "milestone_ids", [link.milestone_id for link in change.milestone_links]
        )
        issue_ids = changes.pop("issue_ids", [link.issue_id for link in change.issue_links])
        risk_ids = changes.pop("risk_ids", [link.risk_id for link in change.risk_links])
        await self._validate_change_links(
            project_id,
            task_ids=task_ids,
            milestone_ids=milestone_ids,
            issue_ids=issue_ids,
            risk_ids=risk_ids,
        )
        before = {key: str(getattr(change, key)) for key in changes}
        for key, value in changes.items():
            setattr(change, key, value)
        await self.repository.set_change_links(
            project_id,
            change.id,
            task_ids=task_ids,
            milestone_ids=milestone_ids,
            issue_ids=issue_ids,
            risk_ids=risk_ids,
        )
        self.audit.record(
            project_id=project_id,
            action="change_request.updated",
            entity_type="change_request",
            entity_id=change.id,
            changes={"before": before, "fields": list(changes)},
        )
        await self.session.commit()
        return self._change_read(await self._change_or_404(project_id, change.id))

    async def _transition_change(
        self,
        project_id: UUID,
        change_id: UUID,
        *,
        allowed_from: set[ChangeStatus],
        target: ChangeStatus,
        action: str,
        decision: str | None = None,
    ) -> ChangeRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        change = await self._change_or_404(project_id, change_id)
        if change.status == target:
            return self._change_read(change)
        if change.status not in allowed_from:
            raise AppError(
                code="invalid_change_transition",
                message=f"Change request cannot move from {change.status.value} to {target.value}.",
                status_code=409,
            )
        previous = change.status
        change.status = target
        if target in (ChangeStatus.APPROVED, ChangeStatus.REJECTED):
            change.decision = decision
            change.decision_date = date.today()
        self.audit.record(
            project_id=project_id,
            action=action,
            entity_type="change_request",
            entity_id=change.id,
            changes={"from": previous.value, "to": target.value, "decision": decision},
        )
        if target == ChangeStatus.APPROVED:
            MemoryService.record_system_log(
                self.session,
                actor_user_id=self.owner_user_id,
                project_id=project_id,
                entry_type=ProjectLogType.CHANGE,
                title=f"Change approved: {change.title}",
                description=decision,
                entity_type=MemoryEntityType.CHANGE_REQUEST,
                entity_id=change.id,
            )
        await self.session.commit()
        return self._change_read(await self._change_or_404(project_id, change.id))

    async def submit_change(self, project_id: UUID, change_id: UUID) -> ChangeRead:
        return await self._transition_change(
            project_id,
            change_id,
            allowed_from={ChangeStatus.DRAFT},
            target=ChangeStatus.PENDING,
            action="change_request.submitted",
        )

    async def approve_change(
        self, project_id: UUID, change_id: UUID, data: ChangeDecision
    ) -> ChangeRead:
        return await self._transition_change(
            project_id,
            change_id,
            allowed_from={ChangeStatus.PENDING},
            target=ChangeStatus.APPROVED,
            action="change_request.approved",
            decision=data.decision,
        )

    async def reject_change(
        self, project_id: UUID, change_id: UUID, data: ChangeDecision
    ) -> ChangeRead:
        return await self._transition_change(
            project_id,
            change_id,
            allowed_from={ChangeStatus.PENDING},
            target=ChangeStatus.REJECTED,
            action="change_request.rejected",
            decision=data.decision,
        )

    async def implement_change(self, project_id: UUID, change_id: UUID) -> ChangeRead:
        return await self._transition_change(
            project_id,
            change_id,
            allowed_from={ChangeStatus.APPROVED},
            target=ChangeStatus.IMPLEMENTED,
            action="change_request.implemented",
        )

    async def cancel_change(self, project_id: UUID, change_id: UUID) -> ChangeRead:
        return await self._transition_change(
            project_id,
            change_id,
            allowed_from={ChangeStatus.DRAFT, ChangeStatus.PENDING, ChangeStatus.APPROVED},
            target=ChangeStatus.CANCELLED,
            action="change_request.cancelled",
        )

    async def summary(self, project_id: UUID) -> ControlSummary:
        await self._project_or_404(project_id)
        values = await self.repository.summary_counts(project_id)
        return ControlSummary(
            open_risks=values[0],
            high_critical_risks=values[1],
            open_issues=values[2],
            critical_issues=values[3],
            pending_changes=values[4],
        )
