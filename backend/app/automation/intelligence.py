from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from app.analytics.control import RiskSeverity, risk_score, risk_severity
from app.analytics.intelligence import ProjectFacts
from app.models.control import ControlPriority, IssueStatus, RiskStatus
from app.models.intelligence import AlertSeverity, HealthStatus
from app.models.milestone import MilestoneStatus
from app.models.project import ProjectStatus
from app.models.task import TaskPriority, TaskStatus
from app.schemas.intelligence import AutomationRuleRead, HealthRead
from app.schemas.people import WorkloadStatus
from app.schemas.scheduling import DeadlineStatus

RULES = [
    AutomationRuleRead(
        key="task_overdue",
        trigger="work.changed",
        conditions=["task overdue", "task blocked > 3 days"],
        actions=["reconcile alert", "recalculate health", "audit on state change"],
        enabled=True,
    ),
    AutomationRuleRead(
        key="milestone_deadline",
        trigger="work.changed",
        conditions=["milestone overdue", "milestone due in 7 days", "milestone at risk"],
        actions=["reconcile alert", "recalculate health"],
        enabled=True,
    ),
    AutomationRuleRead(
        key="budget_threshold",
        trigger="finance.changed",
        conditions=["utilization >= 75%", "forecast exceeds plan"],
        actions=["reconcile alert", "recalculate health"],
        enabled=True,
    ),
    AutomationRuleRead(
        key="critical_risk",
        trigger="control.changed",
        conditions=["active high or critical risk"],
        actions=["reconcile alert", "recalculate health"],
        enabled=True,
    ),
    AutomationRuleRead(
        key="critical_issue",
        trigger="control.changed",
        conditions=["open critical issue", "issue unresolved > 14 days"],
        actions=["reconcile alert", "recalculate health"],
        enabled=True,
    ),
    AutomationRuleRead(
        key="workload_overload",
        trigger="people_or_work.changed",
        conditions=["member workload is high"],
        actions=["reconcile alert", "recalculate health"],
        enabled=True,
    ),
    AutomationRuleRead(
        key="project_deadline",
        trigger="project.changed",
        conditions=["deadline overdue", "deadline due in 14 days"],
        actions=["reconcile alert", "recalculate health"],
        enabled=True,
    ),
    AutomationRuleRead(
        key="advanced_schedule",
        trigger="schedule.changed",
        conditions=[
            "critical task blocked",
            "projected milestone/deadline late",
            "baseline variance > 7 days",
            "dependency violation",
        ],
        actions=["reconcile alert", "recalculate health", "audit on state change"],
        enabled=True,
    ),
    AutomationRuleRead(
        key="health_threshold",
        trigger="intelligence.recalculated",
        conditions=["health at risk or critical"],
        actions=["reconcile alert", "audit", "project log for material state"],
        enabled=True,
    ),
]


@dataclass(frozen=True)
class AlertCondition:
    rule_type: str
    condition_key: str
    severity: AlertSeverity
    title_key: str
    reason_key: str
    evidence: dict
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


def evaluate_conditions(
    facts: ProjectFacts, health: HealthRead, today: date
) -> list[AlertCondition]:
    result: list[AlertCondition] = []
    active_tasks = [
        t for t in facts.tasks if t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
    ]
    for task in active_tasks:
        if task.due_date and task.due_date < today:
            days = (today - task.due_date).days
            severity = (
                AlertSeverity.CRITICAL
                if task.priority == TaskPriority.CRITICAL or days > 7
                else AlertSeverity.WARNING
            )
            result.append(
                AlertCondition(
                    "task_overdue",
                    f"task_overdue:{task.id}",
                    severity,
                    "intelligence.alerts.taskOverdue.title",
                    "intelligence.alerts.taskOverdue.reason",
                    {"title": task.title, "days": days, "due_date": task.due_date.isoformat()},
                    "task",
                    task.id,
                )
            )
        if task.status == TaskStatus.BLOCKED and task.updated_at.date() <= today - timedelta(
            days=3
        ):
            days = (today - task.updated_at.date()).days
            result.append(
                AlertCondition(
                    "task_blocked",
                    f"task_blocked:{task.id}",
                    AlertSeverity.CRITICAL
                    if task.priority == TaskPriority.CRITICAL
                    else AlertSeverity.WARNING,
                    "intelligence.alerts.taskBlocked.title",
                    "intelligence.alerts.taskBlocked.reason",
                    {"title": task.title, "days": days},
                    "task",
                    task.id,
                )
            )
    for milestone in facts.milestones:
        if milestone.status == MilestoneStatus.COMPLETED or milestone.due_date is None:
            continue
        if milestone.due_date < today:
            result.append(
                AlertCondition(
                    "milestone_deadline",
                    f"milestone_overdue:{milestone.id}",
                    AlertSeverity.CRITICAL,
                    "intelligence.alerts.milestoneOverdue.title",
                    "intelligence.alerts.milestoneOverdue.reason",
                    {"title": milestone.title, "days": (today - milestone.due_date).days},
                    "milestone",
                    milestone.id,
                )
            )
        elif milestone.due_date <= today + timedelta(days=7):
            result.append(
                AlertCondition(
                    "milestone_deadline",
                    f"milestone_approaching:{milestone.id}",
                    AlertSeverity.WARNING,
                    "intelligence.alerts.milestoneApproaching.title",
                    "intelligence.alerts.milestoneApproaching.reason",
                    {"title": milestone.title, "days": (milestone.due_date - today).days},
                    "milestone",
                    milestone.id,
                )
            )
        if milestone.status == MilestoneStatus.AT_RISK:
            result.append(
                AlertCondition(
                    "milestone_deadline",
                    f"milestone_at_risk:{milestone.id}",
                    AlertSeverity.WARNING,
                    "intelligence.alerts.milestoneAtRisk.title",
                    "intelligence.alerts.milestoneAtRisk.reason",
                    {"title": milestone.title},
                    "milestone",
                    milestone.id,
                )
            )
    utilization = facts.finance.budget_utilization
    if utilization is not None and utilization >= 75:
        severity = AlertSeverity.CRITICAL if utilization > 90 else AlertSeverity.WARNING
        result.append(
            AlertCondition(
                "budget_threshold",
                "budget_utilization:project",
                severity,
                "intelligence.alerts.budgetUtilization.title",
                "intelligence.alerts.budgetUtilization.reason",
                {"utilization": float(utilization)},
                "project",
                facts.project.id,
            )
        )
    if facts.finance.planned_budget > 0 and facts.finance.forecast > facts.finance.planned_budget:
        result.append(
            AlertCondition(
                "budget_threshold",
                "budget_forecast:project",
                AlertSeverity.CRITICAL,
                "intelligence.alerts.budgetForecast.title",
                "intelligence.alerts.budgetForecast.reason",
                {
                    "forecast": float(facts.finance.forecast),
                    "planned": float(facts.finance.planned_budget),
                },
                "project",
                facts.project.id,
            )
        )
    for risk in facts.risks:
        if risk.status == RiskStatus.CLOSED:
            continue
        severity = risk_severity(risk_score(risk.probability, risk.impact))
        if severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL):
            result.append(
                AlertCondition(
                    "critical_risk",
                    f"risk_severity:{risk.id}",
                    AlertSeverity.CRITICAL
                    if severity == RiskSeverity.CRITICAL
                    else AlertSeverity.WARNING,
                    "intelligence.alerts.risk.title",
                    "intelligence.alerts.risk.reason",
                    {
                        "title": risk.title,
                        "score": risk_score(risk.probability, risk.impact),
                        "severity": severity.value,
                    },
                    "risk",
                    risk.id,
                )
            )
    for issue in facts.issues:
        if issue.status in (IssueStatus.RESOLVED, IssueStatus.CLOSED):
            continue
        if issue.priority == ControlPriority.CRITICAL:
            result.append(
                AlertCondition(
                    "critical_issue",
                    f"critical_issue:{issue.id}",
                    AlertSeverity.CRITICAL,
                    "intelligence.alerts.criticalIssue.title",
                    "intelligence.alerts.criticalIssue.reason",
                    {"title": issue.title},
                    "issue",
                    issue.id,
                )
            )
        elif issue.identified_date <= today - timedelta(days=14):
            result.append(
                AlertCondition(
                    "critical_issue",
                    f"aged_issue:{issue.id}",
                    AlertSeverity.WARNING,
                    "intelligence.alerts.agedIssue.title",
                    "intelligence.alerts.agedIssue.reason",
                    {"title": issue.title, "days": (today - issue.identified_date).days},
                    "issue",
                    issue.id,
                )
            )
    for workload in facts.workloads:
        if workload.workload_status == WorkloadStatus.HIGH:
            result.append(
                AlertCondition(
                    "workload_overload",
                    f"workload:{workload.member_id}",
                    AlertSeverity.WARNING,
                    "intelligence.alerts.workload.title",
                    "intelligence.alerts.workload.reason",
                    {
                        "name": workload.name,
                        "active_tasks": workload.active_task_count,
                        "overdue_tasks": workload.overdue_task_count,
                        "availability": workload.availability_percent,
                    },
                    "project_member",
                    workload.member_id,
                )
            )
    if facts.project.target_end_date and facts.project.status != ProjectStatus.COMPLETED:
        days = (facts.project.target_end_date - today).days
        if days < 0:
            result.append(
                AlertCondition(
                    "project_deadline",
                    "project_deadline:project",
                    AlertSeverity.CRITICAL,
                    "intelligence.alerts.projectOverdue.title",
                    "intelligence.alerts.projectOverdue.reason",
                    {"days": abs(days)},
                    "project",
                    facts.project.id,
                )
            )
        elif days <= 14:
            result.append(
                AlertCondition(
                    "project_deadline",
                    "project_deadline:project",
                    AlertSeverity.WARNING,
                    "intelligence.alerts.projectDeadline.title",
                    "intelligence.alerts.projectDeadline.reason",
                    {"days": days},
                    "project",
                    facts.project.id,
                )
            )
    if facts.schedule:
        schedule = facts.schedule
        if schedule.deadline_impact.status == DeadlineStatus.LATE:
            result.append(
                AlertCondition(
                    "advanced_schedule",
                    "schedule_projected_late:project",
                    AlertSeverity.CRITICAL,
                    "intelligence.alerts.scheduleProjectedLate.title",
                    "intelligence.alerts.scheduleProjectedLate.reason",
                    {
                        "variance_days": schedule.deadline_impact.variance_days,
                        "projected_finish": schedule.deadline_impact.projected_finish.isoformat()
                        if schedule.deadline_impact.projected_finish
                        else None,
                    },
                    "project",
                    facts.project.id,
                )
            )
        for milestone in schedule.milestones:
            if milestone.status == DeadlineStatus.LATE:
                result.append(
                    AlertCondition(
                        "advanced_schedule",
                        f"schedule_milestone_late:{milestone.id}",
                        AlertSeverity.CRITICAL,
                        "intelligence.alerts.scheduleMilestoneLate.title",
                        "intelligence.alerts.scheduleMilestoneLate.reason",
                        {
                            "title": milestone.title,
                            "variance_days": (
                                milestone.projected_date - milestone.current_date
                            ).days
                            if milestone.projected_date and milestone.current_date
                            else None,
                        },
                        "milestone",
                        milestone.id,
                    )
                )
        for task in schedule.tasks:
            if task.finish_variance is not None and task.finish_variance > 7:
                result.append(
                    AlertCondition(
                        "advanced_schedule",
                        f"schedule_baseline_variance:{task.id}",
                        AlertSeverity.WARNING,
                        "intelligence.alerts.scheduleVariance.title",
                        "intelligence.alerts.scheduleVariance.reason",
                        {"title": task.title, "variance_days": task.finish_variance},
                        "task",
                        task.id,
                    )
                )
        by_id = {task.id: task for task in schedule.tasks}
        for dependency in schedule.dependencies:
            predecessor = by_id.get(dependency.predecessor_id)
            successor = by_id.get(dependency.successor_id)
            if (
                predecessor
                and successor
                and predecessor.finish
                and successor.start
                and successor.start <= predecessor.finish
            ):
                result.append(
                    AlertCondition(
                        "advanced_schedule",
                        f"schedule_dependency_violation:{predecessor.id}:{successor.id}",
                        AlertSeverity.WARNING,
                        "intelligence.alerts.scheduleDependency.title",
                        "intelligence.alerts.scheduleDependency.reason",
                        {"predecessor": predecessor.title, "successor": successor.title},
                        "task",
                        successor.id,
                    )
                )
    if health.status in (HealthStatus.AT_RISK, HealthStatus.CRITICAL):
        result.append(
            AlertCondition(
                "health_threshold",
                "health:project",
                AlertSeverity.CRITICAL
                if health.status == HealthStatus.CRITICAL
                else AlertSeverity.WARNING,
                "intelligence.alerts.health.title",
                "intelligence.alerts.health.reason",
                {"score": health.score, "status": health.status.value},
                "project",
                facts.project.id,
            )
        )
    return result
