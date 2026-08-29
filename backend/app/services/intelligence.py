from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.intelligence import ProjectFacts, calculate_health, calculate_kpis
from app.automation.intelligence import RULES, evaluate_conditions
from app.core.errors import AppError
from app.models.intelligence import Alert, AlertSeverity, AlertStatus, HealthSnapshot, HealthStatus
from app.models.memory import MemorySource, ProjectLogEntry, ProjectLogType
from app.repositories.intelligence import IntelligenceRepository
from app.schemas.intelligence import (
    AlertRead,
    HealthHistoryItem,
    HealthRead,
    IntelligenceRead,
    KPIValue,
    PortfolioIntelligence,
    PortfolioProjectIntelligence,
)
from app.services.audit import AuditService
from app.services.finance import FinanceService
from app.services.people import PeopleService


class ProjectIntelligenceService:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.repository = IntelligenceRepository(session, owner_user_id)
        self.audit = AuditService(session, owner_user_id)

    async def _facts(self, project_id: UUID) -> ProjectFacts:
        project = await self.repository.project(project_id)
        if project is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        rows = await self.repository.project_facts(project_id)
        finance = (
            await FinanceService(self.session, self.owner_user_id).analytics(project_id)
        ).totals
        workloads = await PeopleService(self.session, self.owner_user_id).workload(project_id)
        return ProjectFacts(
            project=project,
            tasks=rows["tasks"],
            milestones=rows["milestones"],
            finance=finance,
            workloads=workloads,
            objectives=rows["objectives"],
            criteria=rows["criteria"],
            risks=rows["risks"],
            issues=rows["issues"],
            changes=rows["changes"],
            action_statuses=[item.status for item in rows["actions"]],
            decisions=rows["decisions"],
            log_entries=rows["logs"],
        )

    async def _health(self, facts: ProjectFacts, now: datetime) -> HealthRead:
        health = calculate_health(facts, now.date(), now)
        health.history = [
            HealthHistoryItem.model_validate(item)
            for item in await self.repository.history(facts.project.id)
        ]
        return health

    async def kpis(self, project_id: UUID) -> list[KPIValue]:
        return calculate_kpis(await self._facts(project_id), date.today())

    async def health(self, project_id: UUID) -> HealthRead:
        facts = await self._facts(project_id)
        return await self._health(facts, datetime.now(UTC))

    async def list_alerts(
        self,
        project_id: UUID,
        *,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
    ) -> list[AlertRead]:
        if await self.repository.project(project_id) is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        return [
            AlertRead.model_validate(item)
            for item in await self.repository.alerts(project_id, status=status, severity=severity)
        ]

    async def intelligence(self, project_id: UUID) -> IntelligenceRead:
        facts = await self._facts(project_id)
        now = datetime.now(UTC)
        alerts = await self.repository.alerts(project_id)
        return IntelligenceRead(
            project_id=project_id,
            kpis=calculate_kpis(facts, now.date()),
            health=await self._health(facts, now),
            alerts=[AlertRead.model_validate(item) for item in alerts],
            automation_rules=RULES,
        )

    def _log(self, project_id: UUID, title: str, description: str) -> None:
        self.session.add(
            ProjectLogEntry(
                project_id=project_id,
                type=ProjectLogType.NOTE,
                title=title,
                description=description,
                source=MemorySource.SYSTEM,
                created_by_user_id=self.owner_user_id,
            )
        )

    async def _record_snapshot(self, facts: ProjectFacts, health: HealthRead, trigger: str) -> bool:
        if health.score is None or health.status is None:
            return False
        latest = await self.repository.latest_snapshot(facts.project.id)
        dimensions = [item.model_dump(mode="json") for item in health.dimensions]
        drivers = [item.model_dump(mode="json") for item in health.drivers]
        material = (
            latest is None
            or latest.score != health.score
            or latest.status != health.status
            or latest.dimensions != dimensions
            or latest.drivers != drivers
        )
        if not material:
            return False
        self.session.add(
            HealthSnapshot(
                project_id=facts.project.id,
                score=health.score,
                status=health.status,
                dimensions=dimensions,
                drivers=drivers,
                trigger=trigger,
            )
        )
        if latest is None or latest.status != health.status:
            self.audit.record(
                project_id=facts.project.id,
                action="health.status_changed",
                entity_type="project_health",
                entity_id=facts.project.id,
                changes={
                    "from": latest.status.value if latest else None,
                    "to": health.status.value,
                    "score": health.score,
                },
            )
            if health.status in (HealthStatus.AT_RISK, HealthStatus.CRITICAL):
                self._log(
                    facts.project.id,
                    f"Project health changed to {health.status.value}",
                    f"Deterministic health score is {health.score}.",
                )
        return True

    async def _reconcile_alerts(
        self, facts: ProjectFacts, health: HealthRead, now: datetime
    ) -> None:
        conditions = evaluate_conditions(facts, health, now.date())
        existing = {
            item.condition_key: item for item in await self.repository.alerts(facts.project.id)
        }
        active_keys = {condition.condition_key for condition in conditions}
        for condition in conditions:
            alert = existing.get(condition.condition_key)
            state_change = None
            if alert is None:
                alert = Alert(
                    project_id=facts.project.id,
                    rule_type=condition.rule_type,
                    condition_key=condition.condition_key,
                    severity=condition.severity,
                    title_key=condition.title_key,
                    reason_key=condition.reason_key,
                    evidence=condition.evidence,
                    related_entity_type=condition.related_entity_type,
                    related_entity_id=condition.related_entity_id,
                    status=AlertStatus.ACTIVE,
                    first_detected_at=now,
                    last_detected_at=now,
                )
                self.session.add(alert)
                await self.session.flush()
                state_change = "generated"
            else:
                previous_severity = alert.severity
                if alert.status == AlertStatus.RESOLVED:
                    alert.status = AlertStatus.ACTIVE
                    alert.acknowledged_at = None
                    alert.read_at = None
                    alert.resolved_at = None
                    state_change = "reactivated"
                elif (
                    previous_severity != condition.severity
                    and condition.severity == AlertSeverity.CRITICAL
                ):
                    alert.status = AlertStatus.ACTIVE
                    alert.acknowledged_at = None
                    state_change = "escalated"
                alert.rule_type = condition.rule_type
                alert.severity = condition.severity
                alert.title_key = condition.title_key
                alert.reason_key = condition.reason_key
                alert.evidence = condition.evidence
                alert.last_detected_at = now
            if state_change:
                self.audit.record(
                    project_id=facts.project.id,
                    action=f"alert.{state_change}",
                    entity_type="alert",
                    entity_id=alert.id,
                    changes={"rule": alert.rule_type, "severity": alert.severity.value},
                )
                self.audit.record(
                    project_id=facts.project.id,
                    action="automation.rule_executed",
                    entity_type="automation_rule",
                    entity_id=alert.id,
                    changes={"rule": alert.rule_type, "result": state_change},
                )
                if alert.severity == AlertSeverity.CRITICAL:
                    self._log(
                        facts.project.id,
                        "Critical alert generated",
                        f"Rule {alert.rule_type} detected a critical condition.",
                    )
        for key, alert in existing.items():
            if key in active_keys or alert.status == AlertStatus.RESOLVED:
                continue
            was_critical = alert.severity == AlertSeverity.CRITICAL
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = now
            self.audit.record(
                project_id=facts.project.id,
                action="alert.resolved",
                entity_type="alert",
                entity_id=alert.id,
                changes={"rule": alert.rule_type},
            )
            self.audit.record(
                project_id=facts.project.id,
                action="automation.rule_executed",
                entity_type="automation_rule",
                entity_id=alert.id,
                changes={"rule": alert.rule_type, "result": "resolved"},
            )
            if was_critical:
                self._log(
                    facts.project.id,
                    "Critical condition resolved",
                    f"Rule {alert.rule_type} is no longer active.",
                )

    async def recalculate(self, project_id: UUID, trigger: str = "explicit") -> IntelligenceRead:
        facts = await self._facts(project_id)
        if facts.project.archived_at is not None:
            return await self.intelligence(project_id)
        now = datetime.now(UTC)
        health = await self._health(facts, now)
        await self._record_snapshot(facts, health, trigger)
        await self._reconcile_alerts(facts, health, now)
        await self.session.commit()
        return await self.intelligence(project_id)

    async def acknowledge(self, project_id: UUID, alert_id: UUID) -> AlertRead:
        project = await self.repository.project(project_id)
        if project is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        if project.archived_at is not None:
            raise AppError(
                code="project_archived", message="Archived projects are read-only.", status_code=409
            )
        alert = await self.repository.alert(project_id, alert_id)
        if alert is None:
            raise AppError(code="alert_not_found", message="Alert not found.", status_code=404)
        if alert.status == AlertStatus.RESOLVED:
            raise AppError(
                code="alert_resolved",
                message="Resolved alerts cannot be acknowledged.",
                status_code=409,
            )
        if alert.status != AlertStatus.ACKNOWLEDGED:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now(UTC)
            alert.read_at = alert.read_at or alert.acknowledged_at
            self.audit.record(
                project_id=project_id,
                action="alert.acknowledged",
                entity_type="alert",
                entity_id=alert.id,
            )
            await self.session.commit()
            await self.session.refresh(alert)
        return AlertRead.model_validate(alert)

    async def mark_read(self, project_id: UUID, alert_id: UUID) -> AlertRead:
        if await self.repository.project(project_id) is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        alert = await self.repository.alert(project_id, alert_id)
        if alert is None:
            raise AppError(code="alert_not_found", message="Alert not found.", status_code=404)
        if alert.read_at is None:
            alert.read_at = datetime.now(UTC)
            await self.session.commit()
            await self.session.refresh(alert)
        return AlertRead.model_validate(alert)

    async def portfolio(self) -> PortfolioIntelligence:
        project_rows: list[PortfolioProjectIntelligence] = []
        critical_alerts = 0
        for project in await self.repository.portfolio_projects():
            facts = await self._facts(project.id)
            now = datetime.now(UTC)
            health = calculate_health(facts, now.date(), now)
            kpis = {item.key: item for item in calculate_kpis(facts, now.date())}
            alerts = await self.repository.alerts(project.id)
            active_alerts = [item for item in alerts if item.status != AlertStatus.RESOLVED]
            critical_alerts += sum(
                item.severity == AlertSeverity.CRITICAL for item in active_alerts
            )
            project_rows.append(
                PortfolioProjectIntelligence(
                    project_id=project.id,
                    project_name=project.name,
                    project_code=project.code,
                    health_score=health.score,
                    health_status=health.status,
                    overdue_tasks=int(kpis["overdue_tasks"].value or 0),
                    high_critical_risks=int(kpis["high_risks"].value or 0)
                    + int(kpis["critical_risks"].value or 0),
                    critical_issues=int(kpis["critical_issues"].value or 0),
                    budget_status=str(kpis["finance_status"].value),
                    active_alerts=len(active_alerts),
                )
            )
        return PortfolioIntelligence(
            healthy_projects=sum(p.health_status == HealthStatus.HEALTHY for p in project_rows),
            watch_projects=sum(p.health_status == HealthStatus.WATCH for p in project_rows),
            at_risk_projects=sum(p.health_status == HealthStatus.AT_RISK for p in project_rows),
            critical_projects=sum(p.health_status == HealthStatus.CRITICAL for p in project_rows),
            active_critical_alerts=critical_alerts,
            total_overdue_tasks=sum(p.overdue_tasks for p in project_rows),
            total_high_critical_risks=sum(p.high_critical_risks for p in project_rows),
            projects=project_rows,
        )
