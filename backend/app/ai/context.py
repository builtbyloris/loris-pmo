import json
import unicodedata
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.control import risk_score, risk_severity
from app.core.errors import AppError
from app.models.control import ChangeStatus, IssueStatus, RiskStatus
from app.models.memory import ActionItemStatus, Meeting
from app.models.task import TaskPriority, TaskStatus
from app.models.task_dependency import TaskDependency
from app.repositories.intelligence import IntelligenceRepository
from app.schemas.ai import AIEvidenceRead, AIEvidenceType
from app.services.finance import FinanceService
from app.services.intelligence import ProjectIntelligenceService
from app.services.people import PeopleService
from app.services.work_planning import WorkPlanningService

TASK_LIMIT = 12
MILESTONE_LIMIT = 8
CONTROL_LIMIT = 8
MEMORY_LIMIT = 6
ACTION_LIMIT = 8
ALERT_LIMIT = 10
TEXT_LIMIT = 800


@dataclass(frozen=True)
class ProjectContext:
    sections: dict[str, object]
    evidence: dict[str, AIEvidenceRead]
    topics: tuple[str, ...]

    def prompt_json(self) -> str:
        return json.dumps(self.sections, ensure_ascii=False, separators=(",", ":"), default=str)


TOPIC_KEYWORDS = {
    "work": {
        "task",
        "tasks",
        "schedule",
        "deadline",
        "late",
        "overdue",
        "blocked",
        "milestone",
        "attivita",
        "pianificazione",
        "scadenza",
        "ritardo",
        "bloccata",
    },
    "finance": {
        "budget",
        "cost",
        "costs",
        "expense",
        "expenses",
        "forecast",
        "spend",
        "costo",
        "costi",
        "spesa",
        "spese",
        "previsione",
    },
    "control": {
        "risk",
        "risks",
        "issue",
        "issues",
        "change",
        "changes",
        "rischio",
        "rischi",
        "problema",
        "problemi",
        "cambiamento",
        "modifica",
    },
    "people": {
        "team",
        "people",
        "person",
        "workload",
        "overloaded",
        "resource",
        "resources",
        "squadra",
        "persone",
        "carico",
        "sovraccarico",
        "risorsa",
        "risorse",
    },
    "memory": {
        "changed",
        "recently",
        "meeting",
        "decision",
        "history",
        "log",
        "cambiato",
        "recente",
        "riunione",
        "decisione",
        "storico",
    },
    "objectives": {
        "objective",
        "objectives",
        "goal",
        "goals",
        "success",
        "obiettivo",
        "obiettivi",
        "successo",
    },
}

ATTENTION_KEYWORDS = {
    "attention",
    "urgent",
    "health",
    "status",
    "priority",
    "priorities",
    "attenzione",
    "urgente",
    "salute",
    "stato",
    "priorita",
}

KPI_TOPICS = {
    "work": {
        "total_tasks",
        "completed_tasks",
        "active_tasks",
        "overdue_tasks",
        "blocked_tasks",
        "task_completion_rate",
        "overdue_task_rate",
        "milestones_at_risk",
        "milestones_approaching",
        "milestone_completion_rate",
    },
    "finance": {
        "planned_budget",
        "actual_cost",
        "committed_cost",
        "forecast",
        "remaining_budget",
        "actual_variance",
        "forecast_variance",
        "budget_utilization",
        "finance_status",
    },
    "control": {
        "open_risks",
        "high_risks",
        "critical_risks",
        "average_active_risk_score",
        "open_issues",
        "critical_issues",
        "pending_change_requests",
    },
    "people": {
        "team_size",
        "overloaded_members",
        "workload_warning_count",
        "overdue_assigned_tasks",
    },
    "objectives": {"total_objectives", "success_criteria_met", "objective_progress"},
    "memory": {"pending_meeting_actions", "recent_decisions", "recent_significant_events"},
}

DIMENSION_TOPICS = {
    "schedule": "work",
    "tasks": "work",
    "budget": "finance",
    "risks": "control",
    "resources": "people",
    "objectives": "objectives",
}

DRIVER_TOPICS = {
    "overdue_tasks": "work",
    "overdue_milestones": "work",
    "critical_risks": "control",
    "critical_issues": "control",
    "overloaded_members": "people",
    "budget_pressure": "finance",
}

ALERT_TOPICS = {
    "task_overdue": "work",
    "task_blocked": "work",
    "milestone_deadline": "work",
    "budget_threshold": "finance",
    "critical_risk": "control",
    "critical_issue": "control",
    "workload_overload": "people",
    "project_deadline": "work",
    "health_threshold": "work",
}


def select_topics(question: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", question.lower())
    plain = "".join(character for character in normalized if not unicodedata.combining(character))
    tokens = set(plain.replace("?", " ").replace("'", " ").split())
    topics = {topic for topic, keywords in TOPIC_KEYWORDS.items() if tokens & keywords}
    if tokens & ATTENTION_KEYWORDS or not topics:
        topics.update(TOPIC_KEYWORDS)
    return tuple(sorted(topics))


def _text(value: str | None, limit: int = TEXT_LIMIT) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned[:limit]


def _value(value: object) -> object:
    return getattr(value, "value", value)


def _date_sort(value: date | None) -> date:
    return value or date.max


class ProjectContextBuilder:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.repository = IntelligenceRepository(session, owner_user_id)

    async def build(self, project_id: UUID, question: str) -> ProjectContext:
        project = await self.repository.project(project_id)
        if project is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        topics = select_topics(question)
        rows = await self.repository.project_facts(project_id)
        intelligence = await ProjectIntelligenceService(
            self.session, self.owner_user_id
        ).intelligence(project_id)
        evidence: dict[str, AIEvidenceRead] = {}

        def add_evidence(
            ref: str,
            kind: AIEvidenceType,
            label: str,
            detail: str,
            entity_id: UUID | None = None,
        ) -> str:
            evidence[ref] = AIEvidenceRead(
                ref=ref,
                type=kind,
                id=entity_id,
                label=label,
                detail=detail,
            )
            return ref

        project_ref = add_evidence(
            f"project:{project.id}",
            AIEvidenceType.PROJECT,
            project.name,
            f"{project.code} · {_value(project.status)} · {_value(project.priority)}",
            project.id,
        )
        sections: dict[str, object] = {
            "project": {
                "evidence_ref": project_ref,
                "name": project.name,
                "code": project.code,
                "description": _text(project.description),
                "status": _value(project.status),
                "priority": _value(project.priority),
                "start_date": project.start_date,
                "target_end_date": project.target_end_date,
                "archived": project.archived_at is not None,
            }
        }

        if "objectives" in topics:
            sections["objectives"] = {
                "items": [
                    {
                        "title": item.title,
                        "description": _text(item.description),
                        "status": _value(item.status),
                    }
                    for item in rows["objectives"][:20]
                ],
                "success_criteria": [
                    {
                        "description": _text(item.description),
                        "target": item.target_value,
                        "status": _value(item.status),
                    }
                    for item in rows["criteria"][:30]
                ],
            }

        health_ref = add_evidence(
            "health:overall",
            AIEvidenceType.HEALTH,
            "Project health",
            f"Score {intelligence.health.score}; status {_value(intelligence.health.status)}",
        )
        kpis = []
        allowed_kpis = set().union(*(KPI_TOPICS[topic] for topic in topics))
        for item in (item for item in intelligence.kpis if item.key in allowed_kpis):
            ref = add_evidence(
                f"kpi:{item.key}",
                AIEvidenceType.KPI,
                item.key,
                f"value={item.value}; unit={item.unit}; status={item.status}",
            )
            kpis.append({**item.model_dump(mode="json"), "evidence_ref": ref})
        dimensions = []
        for item in (
            item for item in intelligence.health.dimensions if DIMENSION_TOPICS[item.key] in topics
        ):
            ref = add_evidence(
                f"health:{item.key}",
                AIEvidenceType.HEALTH,
                f"{item.key} health",
                f"score={item.score}; available={item.available}; reason={item.reason}",
            )
            dimensions.append({**item.model_dump(mode="json"), "evidence_ref": ref})
        active_alerts = [
            item
            for item in intelligence.alerts
            if item.status.value != "RESOLVED"
            and ALERT_TOPICS.get(item.rule_type, "work") in topics
        ]
        alerts = []
        for item in active_alerts[:ALERT_LIMIT]:
            ref = add_evidence(
                f"alert:{item.id}",
                AIEvidenceType.ALERT,
                item.rule_type,
                f"{item.severity.value} · {item.status.value}",
                item.id,
            )
            alerts.append(
                {
                    "evidence_ref": ref,
                    "rule": item.rule_type,
                    "severity": item.severity.value,
                    "status": item.status.value,
                    "evidence": item.evidence,
                }
            )
        sections["intelligence"] = {
            "overall_evidence_ref": health_ref,
            "health": {
                "score": intelligence.health.score,
                "status": _value(intelligence.health.status),
                "dimensions": dimensions,
                "drivers": [
                    item.model_dump(mode="json")
                    for item in intelligence.health.drivers
                    if DRIVER_TOPICS[item.key] in topics
                ],
            },
            "kpis": kpis,
            "active_alerts": alerts,
            "limits": {"alerts": ALERT_LIMIT},
        }

        if "work" in topics:
            active = [
                item
                for item in rows["tasks"]
                if item.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
            ]
            priority = {
                TaskPriority.CRITICAL: 0,
                TaskPriority.HIGH: 1,
                TaskPriority.MEDIUM: 2,
                TaskPriority.LOW: 3,
            }
            today = date.today()
            active.sort(
                key=lambda item: (
                    not bool(item.due_date and item.due_date < today),
                    item.status != TaskStatus.BLOCKED,
                    priority[item.priority],
                    _date_sort(item.due_date),
                    str(item.id),
                )
            )
            selected_tasks = active[:TASK_LIMIT]
            task_items = []
            for item in selected_tasks:
                ref = add_evidence(
                    f"task:{item.id}",
                    AIEvidenceType.TASK,
                    item.title,
                    f"{item.status.value} · {item.priority.value} · due {item.due_date}",
                    item.id,
                )
                task_items.append(
                    {
                        "evidence_ref": ref,
                        "title": item.title,
                        "description": _text(item.description),
                        "status": item.status.value,
                        "priority": item.priority.value,
                        "due_date": item.due_date,
                        "completion_percentage": item.completion_percentage,
                    }
                )
            milestones = await WorkPlanningService(
                self.session, self.owner_user_id
            ).list_milestones(project_id)
            milestones.sort(key=lambda item: (_date_sort(item.due_date), str(item.id)))
            milestone_items = []
            for item in milestones[:MILESTONE_LIMIT]:
                ref = add_evidence(
                    f"milestone:{item.id}",
                    AIEvidenceType.MILESTONE,
                    item.title,
                    f"{item.status.value} · due {item.due_date} · progress {item.progress}",
                    item.id,
                )
                milestone_items.append({**item.model_dump(mode="json"), "evidence_ref": ref})
            selected_ids = {item.id for item in selected_tasks}
            dependencies = list(
                (
                    await self.session.execute(
                        select(TaskDependency).where(TaskDependency.project_id == project_id)
                    )
                ).scalars()
            )
            sections["work"] = {
                "critical_tasks": task_items,
                "milestones": milestone_items,
                "dependencies": [
                    {
                        "source_task_id": str(item.source_task_id),
                        "target_task_id": str(item.target_task_id),
                        "type": item.dependency_type.value,
                    }
                    for item in dependencies
                    if item.source_task_id in selected_ids or item.target_task_id in selected_ids
                ][:20],
                "limits": {"tasks": TASK_LIMIT, "milestones": MILESTONE_LIMIT},
            }

        if "people" in topics:
            workloads = await PeopleService(self.session, self.owner_user_id).workload(project_id)
            workload_items = []
            for item in sorted(
                workloads,
                key=lambda row: (
                    row.workload_status.value != "HIGH",
                    -row.overdue_task_count,
                    row.name,
                ),
            )[:20]:
                ref = add_evidence(
                    f"team_member:{item.member_id}",
                    AIEvidenceType.TEAM_MEMBER,
                    item.name,
                    f"{item.role.value} · workload {item.workload_status.value}",
                    item.member_id,
                )
                workload_items.append({**item.model_dump(mode="json"), "evidence_ref": ref})
            sections["people"] = {"workload": workload_items, "limit": 20}

        if "finance" in topics:
            totals = (
                await FinanceService(self.session, self.owner_user_id).analytics(project_id)
            ).totals
            ref = add_evidence(
                "budget:summary",
                AIEvidenceType.BUDGET,
                "Budget summary",
                f"utilization={totals.budget_utilization}; status={totals.financial_status.value}",
            )
            sections["finance"] = {
                "evidence_ref": ref,
                **totals.model_dump(mode="json"),
            }

        if "control" in topics:
            risks = [item for item in rows["risks"] if item.status != RiskStatus.CLOSED]
            risks.sort(
                key=lambda item: (
                    -risk_score(item.probability, item.impact),
                    -item.identified_date.toordinal(),
                )
            )
            risk_items = []
            for item in risks[:CONTROL_LIMIT]:
                score = risk_score(item.probability, item.impact)
                severity = risk_severity(score)
                ref = add_evidence(
                    f"risk:{item.id}",
                    AIEvidenceType.RISK,
                    item.title,
                    f"score {score} · {severity.value} · {item.status.value}",
                    item.id,
                )
                risk_items.append(
                    {
                        "evidence_ref": ref,
                        "title": item.title,
                        "description": _text(item.description),
                        "score": score,
                        "severity": severity.value,
                        "status": item.status.value,
                        "mitigation": _text(item.mitigation),
                    }
                )
            issue_priority = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            issues = [
                item
                for item in rows["issues"]
                if item.status not in (IssueStatus.RESOLVED, IssueStatus.CLOSED)
            ]
            issues.sort(
                key=lambda item: (
                    issue_priority[item.priority.value],
                    -item.identified_date.toordinal(),
                )
            )
            issue_items = []
            for item in issues[:CONTROL_LIMIT]:
                ref = add_evidence(
                    f"issue:{item.id}",
                    AIEvidenceType.ISSUE,
                    item.title,
                    f"{item.priority.value} · {item.status.value}",
                    item.id,
                )
                issue_items.append(
                    {
                        "evidence_ref": ref,
                        "title": item.title,
                        "description": _text(item.description),
                        "priority": item.priority.value,
                        "status": item.status.value,
                        "estimated_delay_days": item.estimated_delay_days,
                        "estimated_cost": item.estimated_cost,
                    }
                )
            changes = [
                item
                for item in rows["changes"]
                if item.status in (ChangeStatus.DRAFT, ChangeStatus.PENDING, ChangeStatus.APPROVED)
            ]
            changes.sort(key=lambda item: (item.requested_date, str(item.id)), reverse=True)
            change_items = []
            for item in changes[:CONTROL_LIMIT]:
                ref = add_evidence(
                    f"change_request:{item.id}",
                    AIEvidenceType.CHANGE_REQUEST,
                    item.title,
                    f"{item.status.value} · requested {item.requested_date}",
                    item.id,
                )
                change_items.append(
                    {
                        "evidence_ref": ref,
                        "title": item.title,
                        "description": _text(item.description),
                        "reason": _text(item.reason),
                        "status": item.status.value,
                        "budget_impact": item.budget_impact.value,
                        "schedule_impact": item.schedule_impact.value,
                    }
                )
            sections["control"] = {
                "risks": risk_items,
                "issues": issue_items,
                "pending_changes": change_items,
                "limit_per_type": CONTROL_LIMIT,
            }

        if "memory" in topics:
            logs = sorted(
                rows["logs"], key=lambda item: (item.created_at, str(item.id)), reverse=True
            )
            decisions = sorted(
                rows["decisions"], key=lambda item: (item.decision_date, str(item.id)), reverse=True
            )
            meetings = list(
                (
                    await self.session.execute(
                        select(Meeting)
                        .where(Meeting.project_id == project_id)
                        .order_by(Meeting.scheduled_at.desc(), Meeting.id)
                        .limit(MEMORY_LIMIT)
                    )
                ).scalars()
            )
            actions = [
                item
                for item in rows["actions"]
                if item.status in (ActionItemStatus.PROPOSED, ActionItemStatus.CONFIRMED)
            ]
            actions.sort(key=lambda item: (_date_sort(item.due_date), str(item.id)))
            sections["memory"] = self._memory_section(
                logs[:MEMORY_LIMIT],
                decisions[:MEMORY_LIMIT],
                meetings,
                actions[:ACTION_LIMIT],
                add_evidence,
            )

        return ProjectContext(sections=sections, evidence=evidence, topics=topics)

    @staticmethod
    def _memory_section(logs, decisions, meetings, actions, add_evidence) -> dict[str, object]:
        log_items = []
        for item in logs:
            ref = add_evidence(
                f"project_log:{item.id}",
                AIEvidenceType.PROJECT_LOG,
                item.title,
                f"{item.type.value} · {item.created_at}",
                item.id,
            )
            log_items.append(
                {
                    "evidence_ref": ref,
                    "title": item.title,
                    "description": _text(item.description),
                    "type": item.type.value,
                    "created_at": item.created_at,
                }
            )
        decision_items = []
        for item in decisions:
            ref = add_evidence(
                f"decision:{item.id}",
                AIEvidenceType.DECISION,
                item.title,
                f"{item.status.value} · {item.decision_date}",
                item.id,
            )
            decision_items.append(
                {
                    "evidence_ref": ref,
                    "title": item.title,
                    "decision": _text(item.decision),
                    "reason": _text(item.reason),
                    "status": item.status.value,
                    "decision_date": item.decision_date,
                }
            )
        meeting_items = []
        for item in meetings:
            ref = add_evidence(
                f"meeting:{item.id}",
                AIEvidenceType.MEETING,
                item.title,
                f"{item.status.value} · {item.scheduled_at}",
                item.id,
            )
            meeting_items.append(
                {
                    "evidence_ref": ref,
                    "title": item.title,
                    "status": item.status.value,
                    "scheduled_at": item.scheduled_at,
                    "notes": _text(item.notes),
                }
            )
        return {
            "recent_log_entries": log_items,
            "recent_decisions": decision_items,
            "recent_meetings": meeting_items,
            "pending_action_items": [
                {
                    "description": _text(item.description),
                    "status": item.status.value,
                    "due_date": item.due_date,
                }
                for item in actions
            ],
            "limits": {
                "logs": MEMORY_LIMIT,
                "decisions": MEMORY_LIMIT,
                "meetings": MEMORY_LIMIT,
                "actions": ACTION_LIMIT,
            },
        }
