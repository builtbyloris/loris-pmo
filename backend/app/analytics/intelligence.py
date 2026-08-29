from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.analytics.control import RiskSeverity, risk_score, risk_severity
from app.models.control import (
    ChangeRequest,
    ChangeStatus,
    ControlPriority,
    Issue,
    IssueStatus,
    Risk,
    RiskStatus,
)
from app.models.intelligence import AlertSeverity, HealthStatus
from app.models.memory import ActionItemStatus, Decision, ProjectLogEntry
from app.models.milestone import Milestone, MilestoneStatus
from app.models.objective import Objective
from app.models.project import Project, ProjectStatus
from app.models.success_criterion import SuccessCriterion, SuccessCriterionStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.finance import FinancialTotals
from app.schemas.intelligence import HealthDimension, HealthDriver, HealthRead, KPIValue
from app.schemas.people import MemberWorkload, WorkloadStatus

DIMENSION_WEIGHTS = {
    "schedule": 25,
    "budget": 20,
    "tasks": 20,
    "risks": 15,
    "resources": 10,
    "objectives": 10,
}


@dataclass
class ProjectFacts:
    project: Project
    tasks: list[Task]
    milestones: list[Milestone]
    finance: FinancialTotals
    workloads: list[MemberWorkload]
    objectives: list[Objective]
    criteria: list[SuccessCriterion]
    risks: list[Risk]
    issues: list[Issue]
    changes: list[ChangeRequest]
    action_statuses: list[ActionItemStatus]
    decisions: list[Decision]
    log_entries: list[ProjectLogEntry]


def health_status(score: int) -> HealthStatus:
    if score >= 85:
        return HealthStatus.HEALTHY
    if score >= 70:
        return HealthStatus.WATCH
    if score >= 50:
        return HealthStatus.AT_RISK
    return HealthStatus.CRITICAL


def _kpi(key: str, value, unit: str | None = "count", status: str = "normal") -> KPIValue:
    if isinstance(value, Decimal):
        value = float(value)
    return KPIValue(key=key, value=value, unit=unit, status=status)


def unavailable(key: str, reason: str, unit: str | None = None) -> KPIValue:
    return KPIValue(
        key=key, value=None, unit=unit, status="unavailable", available=False, reason=reason
    )


def calculate_kpis(facts: ProjectFacts, today: date) -> list[KPIValue]:
    active_tasks = [
        task for task in facts.tasks if task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
    ]
    completed_tasks = [task for task in facts.tasks if task.status == TaskStatus.DONE]
    eligible_tasks = [task for task in facts.tasks if task.status != TaskStatus.CANCELLED]
    overdue_tasks = [task for task in active_tasks if task.due_date and task.due_date < today]
    blocked_tasks = [task for task in active_tasks if task.status == TaskStatus.BLOCKED]
    milestone_base = [m for m in facts.milestones]
    incomplete_milestones = [m for m in milestone_base if m.status != MilestoneStatus.COMPLETED]
    approaching = [
        m
        for m in incomplete_milestones
        if m.due_date and today <= m.due_date <= today + timedelta(days=7)
    ]
    at_risk = [m for m in incomplete_milestones if m.status == MilestoneStatus.AT_RISK]
    active_risks = [risk for risk in facts.risks if risk.status != RiskStatus.CLOSED]
    severities = [risk_severity(risk_score(r.probability, r.impact)) for r in active_risks]
    open_issues = [
        i for i in facts.issues if i.status not in (IssueStatus.RESOLVED, IssueStatus.CLOSED)
    ]
    pending_changes = [
        change
        for change in facts.changes
        if change.status in (ChangeStatus.DRAFT, ChangeStatus.PENDING)
    ]
    overloaded = [w for w in facts.workloads if w.workload_status == WorkloadStatus.HIGH]
    warnings = [
        w
        for w in facts.workloads
        if w.workload_status in (WorkloadStatus.MEDIUM, WorkloadStatus.HIGH)
    ]
    criteria = [c for c in facts.criteria if c.status != SuccessCriterionStatus.NOT_APPLICABLE]
    recent_cutoff = today - timedelta(days=30)
    totals = facts.finance
    task_rate = (
        round(len(completed_tasks) / len(eligible_tasks) * 100, 1) if eligible_tasks else None
    )
    overdue_rate = (
        round(len(overdue_tasks) / len(eligible_tasks) * 100, 1) if eligible_tasks else None
    )
    milestone_rate = (
        round(
            sum(m.status == MilestoneStatus.COMPLETED for m in milestone_base)
            / len(milestone_base)
            * 100,
            1,
        )
        if milestone_base
        else None
    )
    objective_rate = (
        round(
            sum(c.status == SuccessCriterionStatus.MET for c in criteria) / len(criteria) * 100, 1
        )
        if criteria
        else None
    )
    result = [
        _kpi("total_tasks", len(facts.tasks)),
        _kpi("completed_tasks", len(completed_tasks)),
        _kpi("active_tasks", len(active_tasks)),
        _kpi("overdue_tasks", len(overdue_tasks), status="critical" if overdue_tasks else "normal"),
        _kpi("blocked_tasks", len(blocked_tasks), status="warning" if blocked_tasks else "normal"),
        _kpi("milestones_at_risk", len(at_risk), status="warning" if at_risk else "normal"),
        _kpi(
            "milestones_approaching",
            len(approaching),
            status="warning" if approaching else "normal",
        ),
        _kpi("planned_budget", totals.planned_budget, "currency"),
        _kpi("actual_cost", totals.actual_cost, "currency"),
        _kpi("committed_cost", totals.committed_cost, "currency"),
        _kpi("forecast", totals.forecast, "currency"),
        _kpi(
            "remaining_budget",
            totals.remaining_budget,
            "currency",
            "critical" if totals.remaining_budget < 0 else "normal",
        ),
        _kpi("actual_variance", totals.actual_variance, "currency"),
        _kpi(
            "forecast_variance",
            totals.planned_budget - totals.forecast,
            "currency",
            "critical" if totals.forecast > totals.planned_budget else "normal",
        ),
        _kpi(
            "finance_status",
            totals.financial_status.value,
            "status",
            totals.financial_status.value.lower(),
        ),
        _kpi("open_risks", len(active_risks)),
        _kpi(
            "high_risks",
            severities.count(RiskSeverity.HIGH),
            status="warning" if RiskSeverity.HIGH in severities else "normal",
        ),
        _kpi(
            "critical_risks",
            severities.count(RiskSeverity.CRITICAL),
            status="critical" if RiskSeverity.CRITICAL in severities else "normal",
        ),
        _kpi(
            "average_active_risk_score",
            round(
                sum(risk_score(r.probability, r.impact) for r in active_risks) / len(active_risks),
                1,
            )
            if active_risks
            else 0,
            "score",
        ),
        _kpi("open_issues", len(open_issues)),
        _kpi(
            "critical_issues",
            sum(i.priority == ControlPriority.CRITICAL for i in open_issues),
            status="critical"
            if any(i.priority == ControlPriority.CRITICAL for i in open_issues)
            else "normal",
        ),
        _kpi("pending_change_requests", len(pending_changes)),
        _kpi("team_size", len(facts.workloads)),
        _kpi("overloaded_members", len(overloaded), status="critical" if overloaded else "normal"),
        _kpi("workload_warning_count", len(warnings), status="warning" if warnings else "normal"),
        _kpi(
            "overdue_assigned_tasks",
            sum(w.overdue_task_count for w in facts.workloads),
            status="warning" if any(w.overdue_task_count for w in facts.workloads) else "normal",
        ),
        _kpi("total_objectives", len(facts.objectives)),
        _kpi("success_criteria_met", sum(c.status == SuccessCriterionStatus.MET for c in criteria)),
        _kpi(
            "pending_meeting_actions",
            sum(
                s in (ActionItemStatus.PROPOSED, ActionItemStatus.CONFIRMED)
                for s in facts.action_statuses
            ),
        ),
        _kpi("recent_decisions", sum(d.decision_date >= recent_cutoff for d in facts.decisions)),
        _kpi(
            "recent_significant_events",
            sum(entry.created_at.date() >= recent_cutoff for entry in facts.log_entries),
        ),
    ]
    result.insert(
        5,
        _kpi("task_completion_rate", task_rate, "percent")
        if task_rate is not None
        else unavailable("task_completion_rate", "no_tasks", "percent"),
    )
    result.insert(
        6,
        _kpi("overdue_task_rate", overdue_rate, "percent")
        if overdue_rate is not None
        else unavailable("overdue_task_rate", "no_tasks", "percent"),
    )
    result.insert(
        9,
        _kpi("milestone_completion_rate", milestone_rate, "percent")
        if milestone_rate is not None
        else unavailable("milestone_completion_rate", "no_milestones", "percent"),
    )
    result.insert(
        17,
        _kpi(
            "budget_utilization",
            totals.budget_utilization,
            "percent",
            totals.financial_status.value.lower(),
        )
        if totals.budget_utilization is not None
        else unavailable("budget_utilization", "no_planned_budget", "percent"),
    )
    result.insert(
        -3,
        _kpi("objective_progress", objective_rate, "percent")
        if objective_rate is not None
        else unavailable("objective_progress", "no_measurable_success_criteria", "percent"),
    )
    return result


def _dimension(key: str, score: int | None, reason: str | None, evidence: dict) -> HealthDimension:
    return HealthDimension(
        key=key,
        score=score,
        status=health_status(score) if score is not None else None,
        available=score is not None,
        reason=reason,
        weight=DIMENSION_WEIGHTS[key],
        effective_weight=0,
        evidence=evidence,
    )


def calculate_health(facts: ProjectFacts, today: date, calculated_at) -> HealthRead:
    eligible = [t for t in facts.tasks if t.status != TaskStatus.CANCELLED]
    active = [t for t in eligible if t.status != TaskStatus.DONE]
    overdue = [t for t in active if t.due_date and t.due_date < today]
    blocked = [t for t in active if t.status == TaskStatus.BLOCKED]
    incomplete_ms = [m for m in facts.milestones if m.status != MilestoneStatus.COMPLETED]
    overdue_ms = [m for m in incomplete_ms if m.due_date and m.due_date < today]
    approaching_ms = [
        m for m in incomplete_ms if m.due_date and today <= m.due_date <= today + timedelta(days=7)
    ]
    dated = (
        any(t.due_date for t in eligible)
        or any(m.due_date for m in facts.milestones)
        or facts.project.target_end_date is not None
    )
    schedule_score = None
    if dated:
        schedule_score = (
            100
            - min(40, len(overdue) * 10)
            - min(35, len(overdue_ms) * 20)
            - min(20, len(approaching_ms) * 5)
        )
        if (
            facts.project.target_end_date
            and facts.project.target_end_date < today
            and facts.project.status != ProjectStatus.COMPLETED
        ):
            schedule_score -= 30
        schedule_score = max(0, schedule_score)
    task_score = None
    if eligible:
        completion = sum(t.completion_percentage for t in eligible) / len(eligible)
        task_score = round(
            max(
                0,
                100
                - len(overdue) / len(eligible) * 50
                - len(blocked) / len(eligible) * 30
                - (100 - completion) * 0.2,
            )
        )
    budget_score = None
    if facts.finance.planned_budget > 0 and facts.finance.budget_utilization is not None:
        utilization = float(facts.finance.budget_utilization)
        forecast_percent = float(facts.finance.forecast / facts.finance.planned_budget * 100)
        budget_score = round(
            max(0, 100 - max(0, utilization - 60) * 1.5 - max(0, forecast_percent - 100) * 2)
        )
    active_risks = [r for r in facts.risks if r.status != RiskStatus.CLOSED]
    risk_severities = [risk_severity(risk_score(r.probability, r.impact)) for r in active_risks]
    open_issues = [
        i for i in facts.issues if i.status not in (IssueStatus.RESOLVED, IssueStatus.CLOSED)
    ]
    risk_dimension = max(
        0,
        100
        - risk_severities.count(RiskSeverity.CRITICAL) * 35
        - risk_severities.count(RiskSeverity.HIGH) * 20
        - risk_severities.count(RiskSeverity.MEDIUM) * 8
        - sum(i.priority == ControlPriority.CRITICAL for i in open_issues) * 25
        - sum(i.priority != ControlPriority.CRITICAL for i in open_issues) * 5,
    )
    resource_score = None
    if facts.workloads:
        resource_score = max(
            0,
            100
            - sum(w.workload_status == WorkloadStatus.HIGH for w in facts.workloads) * 30
            - sum(w.workload_status == WorkloadStatus.MEDIUM for w in facts.workloads) * 10,
        )
    criteria = [c for c in facts.criteria if c.status != SuccessCriterionStatus.NOT_APPLICABLE]
    objective_score = (
        round(sum(c.status == SuccessCriterionStatus.MET for c in criteria) / len(criteria) * 100)
        if criteria
        else None
    )
    dimensions = [
        _dimension(
            "schedule",
            schedule_score,
            None if dated else "no_schedule_dates",
            {
                "overdue_tasks": len(overdue),
                "overdue_milestones": len(overdue_ms),
                "approaching_milestones": len(approaching_ms),
            },
        ),
        _dimension(
            "budget",
            budget_score,
            None if budget_score is not None else "no_planned_budget",
            {
                "utilization": float(facts.finance.budget_utilization)
                if facts.finance.budget_utilization is not None
                else None,
                "forecast": float(facts.finance.forecast),
            },
        ),
        _dimension(
            "tasks",
            task_score,
            None if eligible else "no_tasks",
            {"total": len(eligible), "overdue": len(overdue), "blocked": len(blocked)},
        ),
        _dimension(
            "risks",
            risk_dimension,
            None,
            {
                "active": len(active_risks),
                "high": risk_severities.count(RiskSeverity.HIGH),
                "critical": risk_severities.count(RiskSeverity.CRITICAL),
                "critical_issues": sum(i.priority == ControlPriority.CRITICAL for i in open_issues),
            },
        ),
        _dimension(
            "resources",
            resource_score,
            None if facts.workloads else "no_team_members",
            {
                "team_size": len(facts.workloads),
                "overloaded": sum(
                    w.workload_status == WorkloadStatus.HIGH for w in facts.workloads
                ),
            },
        ),
        _dimension(
            "objectives",
            objective_score,
            None if criteria else "no_measurable_success_criteria",
            {
                "criteria": len(criteria),
                "met": sum(c.status == SuccessCriterionStatus.MET for c in criteria),
            },
        ),
    ]
    available_weight = sum(d.weight for d in dimensions if d.available)
    for item in dimensions:
        item.effective_weight = (
            round(item.weight / available_weight * 100, 2)
            if item.available and available_weight
            else 0
        )
    overall = (
        round(sum((d.score or 0) * d.weight for d in dimensions if d.available) / available_weight)
        if available_weight
        else None
    )
    drivers: list[HealthDriver] = []
    driver_data = [
        (
            "overdue_tasks",
            len(overdue),
            AlertSeverity.CRITICAL
            if any(t.priority == TaskPriority.CRITICAL for t in overdue)
            else AlertSeverity.WARNING,
        ),
        ("overdue_milestones", len(overdue_ms), AlertSeverity.CRITICAL),
        ("critical_risks", risk_severities.count(RiskSeverity.CRITICAL), AlertSeverity.CRITICAL),
        (
            "critical_issues",
            sum(i.priority == ControlPriority.CRITICAL for i in open_issues),
            AlertSeverity.CRITICAL,
        ),
        (
            "overloaded_members",
            sum(w.workload_status == WorkloadStatus.HIGH for w in facts.workloads),
            AlertSeverity.WARNING,
        ),
    ]
    for key, count, severity in driver_data:
        if count:
            drivers.append(HealthDriver(key=key, severity=severity, evidence={"count": count}))
    if budget_score is not None and budget_score < 70:
        drivers.append(
            HealthDriver(
                key="budget_pressure",
                severity=AlertSeverity.CRITICAL if budget_score < 50 else AlertSeverity.WARNING,
                evidence={"score": budget_score},
            )
        )
    return HealthRead(
        score=overall,
        status=health_status(overall) if overall is not None else None,
        dimensions=dimensions,
        drivers=drivers,
        calculated_at=calculated_at,
    )
