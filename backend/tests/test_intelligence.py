from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.intelligence import health_status
from app.auth.passwords import hash_password
from app.models.control import ControlPriority, Issue, IssueStatus, Risk, RiskStatus
from app.models.finance import Expense, ExpenseStatus
from app.models.intelligence import Alert, HealthSnapshot, HealthStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.objective import Objective
from app.models.people import Person, ProjectMember, TaskAssignee
from app.models.success_criterion import SuccessCriterion, SuccessCriterionStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.repositories.users import UserRepository

PASSWORD = "a secure intelligence test password"


def test_health_status_thresholds() -> None:
    assert health_status(100) == HealthStatus.HEALTHY
    assert health_status(85) == HealthStatus.HEALTHY
    assert health_status(84) == HealthStatus.WATCH
    assert health_status(70) == HealthStatus.WATCH
    assert health_status(69) == HealthStatus.AT_RISK
    assert health_status(50) == HealthStatus.AT_RISK
    assert health_status(49) == HealthStatus.CRITICAL
    assert health_status(0) == HealthStatus.CRITICAL


async def login_as(
    client: AsyncClient, session: AsyncSession, email: str
) -> tuple[object, dict[str, str]]:
    user = await UserRepository(session).create(email=email, password_hash=hash_password(PASSWORD))
    await session.commit()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return user, {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


async def create_project(
    client: AsyncClient, headers: dict[str, str], code: str, **overrides
) -> dict:
    payload = {
        "name": f"Intelligence {code}",
        "code": code,
        "planned_budget": "0",
        **overrides,
    }
    response = await client.post("/api/v1/projects", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def test_missing_data_is_explicit_and_weights_are_redistributed(
    client: AsyncClient, session: AsyncSession
) -> None:
    _user, headers = await login_as(client, session, "empty-intelligence@example.com")
    project = await create_project(client, headers, "INT-EMPTY")

    response = await client.get(f"/api/v1/projects/{project['id']}/intelligence")
    assert response.status_code == 200
    body = response.json()
    kpis = {item["key"]: item for item in body["kpis"]}
    assert kpis["task_completion_rate"] == {
        "key": "task_completion_rate",
        "value": None,
        "unit": "percent",
        "status": "unavailable",
        "available": False,
        "reason": "no_tasks",
    }
    dimensions = {item["key"]: item for item in body["health"]["dimensions"]}
    assert dimensions["schedule"]["available"] is False
    assert dimensions["budget"]["available"] is False
    assert dimensions["tasks"]["available"] is False
    assert dimensions["resources"]["available"] is False
    assert dimensions["objectives"]["available"] is False
    assert dimensions["risks"]["effective_weight"] == 100
    assert body["health"]["score"] == 100
    assert len(body["automation_rules"]) == 8


async def test_kpis_health_alert_lifecycle_dedup_reappearance_and_portfolio(
    client: AsyncClient, session: AsyncSession
) -> None:
    user, headers = await login_as(client, session, "intelligence@example.com")
    today = date.today()
    project = await create_project(
        client,
        headers,
        "INT-LIVE",
        planned_budget="1000",
        target_end_date=(today + timedelta(days=60)).isoformat(),
    )
    project_id = UUID(project["id"])
    task = Task(
        project_id=project_id,
        title="Critical overdue delivery",
        status=TaskStatus.TODO,
        priority=TaskPriority.CRITICAL,
        due_date=today - timedelta(days=5),
        estimated_effort=Decimal("8"),
    )
    person = Person(owner_user_id=user.id, name="Overloaded Owner")
    member = ProjectMember(
        project_id=project_id,
        person=person,
        availability_percent=0,
    )
    objective = Objective(project_id=project_id, title="Launch")
    session.add_all([task, person, member, objective])
    await session.flush()
    session.add_all(
        [
            TaskAssignee(
                project_id=project_id,
                task_id=task.id,
                project_member_id=member.id,
            ),
            Expense(
                project_id=project_id,
                description="Committed launch cost",
                amount=Decimal("950"),
                date=today,
                status=ExpenseStatus.PENDING,
            ),
            Risk(
                project_id=project_id,
                title="Launch failure",
                probability=5,
                impact=5,
                identified_date=today,
            ),
            Issue(
                project_id=project_id,
                title="Production outage",
                priority=ControlPriority.CRITICAL,
                identified_date=today,
            ),
            SuccessCriterion(
                project_id=project_id,
                objective_id=objective.id,
                description="Release accepted",
                status=SuccessCriterionStatus.MET,
            ),
        ]
    )
    await session.commit()

    first = await client.post(
        f"/api/v1/projects/{project['id']}/intelligence/recalculate",
        headers=headers,
    )
    assert first.status_code == 200, first.text
    body = first.json()
    kpis = {item["key"]: item for item in body["kpis"]}
    assert kpis["overdue_tasks"]["value"] == 1
    assert kpis["budget_utilization"]["value"] == 95.0
    assert kpis["critical_risks"]["value"] == 1
    assert kpis["critical_issues"]["value"] == 1
    assert kpis["overloaded_members"]["value"] == 1
    dimensions = {item["key"]: item for item in body["health"]["dimensions"]}
    assert body["health"]["score"] == 61
    assert body["health"]["status"] == "AT_RISK"
    assert dimensions["schedule"]["score"] == 90
    assert dimensions["budget"]["score"] == 48
    assert dimensions["tasks"]["score"] == 30
    assert dimensions["risks"]["score"] == 40
    assert dimensions["resources"]["score"] == 70
    assert dimensions["objectives"]["score"] == 100
    active = [item for item in body["alerts"] if item["status"] != "RESOLVED"]
    assert {item["rule_type"] for item in active} >= {
        "task_overdue",
        "budget_threshold",
        "critical_risk",
        "critical_issue",
        "workload_overload",
    }
    first_alert_count = len(body["alerts"])
    first_snapshot_count = (
        await session.execute(select(func.count(HealthSnapshot.id)))
    ).scalar_one()

    second = await client.post(
        f"/api/v1/projects/{project['id']}/intelligence/recalculate",
        headers=headers,
    )
    assert second.status_code == 200
    assert len(second.json()["alerts"]) == first_alert_count
    assert (
        await session.execute(select(func.count(HealthSnapshot.id)))
    ).scalar_one() == first_snapshot_count

    task_alert = next(item for item in active if item["rule_type"] == "task_overdue")
    acknowledged = await client.post(
        f"/api/v1/projects/{project['id']}/alerts/{task_alert['id']}/acknowledge",
        headers=headers,
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "ACKNOWLEDGED"
    first_detected = acknowledged.json()["first_detected_at"]

    risk = (await session.execute(select(Risk).where(Risk.project_id == project_id))).scalar_one()
    issue = (
        await session.execute(select(Issue).where(Issue.project_id == project_id))
    ).scalar_one()
    expense = (
        await session.execute(select(Expense).where(Expense.project_id == project_id))
    ).scalar_one()
    task.status = TaskStatus.DONE
    task.completion_percentage = 100
    risk.status = RiskStatus.CLOSED
    issue.status = IssueStatus.RESOLVED
    expense.status = ExpenseStatus.CANCELLED
    member.availability_percent = 100
    await session.commit()

    resolved = await client.post(
        f"/api/v1/projects/{project['id']}/intelligence/recalculate",
        headers=headers,
    )
    assert resolved.status_code == 200
    resolved_task = next(
        item for item in resolved.json()["alerts"] if item["id"] == task_alert["id"]
    )
    assert resolved_task["status"] == "RESOLVED"

    task.status = TaskStatus.TODO
    task.completion_percentage = 0
    await session.commit()
    reappeared = await client.post(
        f"/api/v1/projects/{project['id']}/intelligence/recalculate",
        headers=headers,
    )
    reappeared_task = next(
        item for item in reappeared.json()["alerts"] if item["id"] == task_alert["id"]
    )
    assert reappeared_task["status"] == "ACTIVE"
    assert reappeared_task["first_detected_at"] == first_detected
    assert reappeared_task["acknowledged_at"] is None
    assert (await session.execute(select(func.count(Alert.id)))).scalar_one() == first_alert_count

    portfolio = (await client.get("/api/v1/portfolio/intelligence")).json()
    assert portfolio["total_overdue_tasks"] == 1
    assert portfolio["projects"][0]["project_id"] == project["id"]

    _other, _other_headers = await login_as(client, session, "other-intelligence@example.com")
    assert (await client.get(f"/api/v1/projects/{project['id']}/intelligence")).status_code == 404


async def test_milestone_and_project_deadline_rules_resolve_automatically(
    client: AsyncClient, session: AsyncSession
) -> None:
    _user, headers = await login_as(client, session, "deadline-intelligence@example.com")
    today = date.today()
    project = await create_project(
        client,
        headers,
        "INT-DATE",
        target_end_date=(today + timedelta(days=10)).isoformat(),
    )
    milestone = Milestone(
        project_id=UUID(project["id"]),
        title="Release gate",
        due_date=today + timedelta(days=3),
        status=MilestoneStatus.AT_RISK,
    )
    session.add(milestone)
    await session.commit()

    response = await client.post(
        f"/api/v1/projects/{project['id']}/intelligence/recalculate",
        headers=headers,
    )
    rules = {
        item["rule_type"] for item in response.json()["alerts"] if item["status"] != "RESOLVED"
    }
    assert "milestone_deadline" in rules
    assert "project_deadline" in rules

    milestone.status = MilestoneStatus.COMPLETED
    update = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert update.status_code == 200
    await session.commit()
    resolved = await client.post(
        f"/api/v1/projects/{project['id']}/intelligence/recalculate",
        headers=headers,
    )
    matching = [
        item
        for item in resolved.json()["alerts"]
        if item["rule_type"] in ("milestone_deadline", "project_deadline")
    ]
    assert matching
    assert all(item["status"] == "RESOLVED" for item in matching)
