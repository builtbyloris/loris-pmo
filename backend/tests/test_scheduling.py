from datetime import date
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.scheduling import ScheduleTask, calculate_cpm, propagate_finish_to_start
from app.auth.passwords import hash_password
from app.models.audit import AuditEvent
from app.models.collaboration import MembershipStatus, ProjectAccessRole, ProjectMembership
from app.repositories.users import UserRepository

PASSWORD = "a secure schedule password"


def test_cpm_exact_offsets_float_and_branching() -> None:
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    tasks = [
        ScheduleTask(a, date(2026, 9, 1), date(2026, 9, 3)),
        ScheduleTask(b, date(2026, 9, 4), date(2026, 9, 6)),
        ScheduleTask(c, date(2026, 9, 4), date(2026, 9, 4)),
        ScheduleTask(d, date(2026, 9, 7), date(2026, 9, 9)),
    ]
    result = calculate_cpm(tasks, {(a, b), (a, c), (b, d), (c, d)})
    assert result.complete is True
    assert result.project_duration_days == 9
    assert result.tasks[a].earliest_start == 0
    assert result.tasks[a].earliest_finish == 2
    assert result.tasks[b].total_float == 0
    assert result.tasks[c].total_float == 2
    assert result.tasks[c].free_float == 2
    assert result.tasks[d].latest_finish == 8
    assert result.critical_task_ids == [a, b, d]
    assert result.critical_sequences == [[a, b, d]]


def test_recursive_propagation_chain_branch_convergence_and_no_mutation() -> None:
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    tasks = [
        ScheduleTask(a, date(2026, 9, 1), date(2026, 9, 3)),
        ScheduleTask(b, date(2026, 9, 4), date(2026, 9, 6)),
        ScheduleTask(c, date(2026, 9, 4), date(2026, 9, 5)),
        ScheduleTask(d, date(2026, 9, 7), date(2026, 9, 9)),
    ]
    projected = propagate_finish_to_start(
        tasks,
        {(a, b), (a, c), (b, d), (c, d)},
        a,
        date(2026, 9, 3),
        date(2026, 9, 5),
    )
    assert projected[a] == (date(2026, 9, 3), date(2026, 9, 5))
    assert projected[b] == (date(2026, 9, 6), date(2026, 9, 8))
    assert projected[c] == (date(2026, 9, 6), date(2026, 9, 7))
    assert projected[d] == (date(2026, 9, 9), date(2026, 9, 11))
    assert tasks[1].start == date(2026, 9, 4)


def test_cpm_disconnected_tasks_have_exact_float() -> None:
    short, long = uuid4(), uuid4()
    result = calculate_cpm(
        [
            ScheduleTask(short, date(2026, 9, 1), date(2026, 9, 2)),
            ScheduleTask(long, date(2026, 9, 1), date(2026, 9, 5)),
        ],
        set(),
    )
    assert result.complete is True
    assert result.project_duration_days == 5
    assert result.tasks[short].total_float == 3
    assert result.tasks[long].total_float == 0


def test_cpm_incomplete_schedule_does_not_expose_partial_float() -> None:
    scheduled, missing = uuid4(), uuid4()
    result = calculate_cpm(
        [
            ScheduleTask(scheduled, date(2026, 9, 1), date(2026, 9, 2)),
            ScheduleTask(missing, None, None),
        ],
        set(),
    )
    assert result.complete is False
    assert result.reasons == ["tasks_missing_valid_dates"]
    assert result.project_duration_days is None
    assert result.tasks == {}
    assert result.critical_task_ids == []
    assert result.critical_sequences == []


async def _login(client: AsyncClient, session: AsyncSession) -> dict:
    owner = await UserRepository(session).create(
        email="schedule-owner@example.com", password_hash=hash_password(PASSWORD)
    )
    await session.commit()
    response = await client.post(
        "/api/v1/auth/login", json={"email": "schedule-owner@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200
    return owner, {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


async def test_schedule_baseline_preview_apply_stale_and_variance(
    client: AsyncClient, session: AsyncSession
) -> None:
    owner, headers = await _login(client, session)
    project = (
        await client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "Schedule E2E",
                "code": "SCHEDULE-E2E",
                "start_date": "2026-09-01",
                "target_end_date": "2026-09-10",
            },
        )
    ).json()
    milestone = (
        await client.post(
            f"/api/v1/projects/{project['id']}/milestones",
            headers=headers,
            json={"title": "Release", "due_date": "2026-09-09"},
        )
    ).json()
    tasks = []
    for title, start, finish in (
        ("A", "2026-09-01", "2026-09-03"),
        ("B", "2026-09-04", "2026-09-06"),
        ("C", "2026-09-07", "2026-09-09"),
    ):
        tasks.append(
            (
                await client.post(
                    f"/api/v1/projects/{project['id']}/tasks",
                    headers=headers,
                    json={
                        "title": title,
                        "start_date": start,
                        "due_date": finish,
                        "milestone_id": milestone["id"],
                    },
                )
            ).json()
        )
    for source, target in zip(tasks, tasks[1:], strict=False):
        response = await client.post(
            f"/api/v1/projects/{project['id']}/task-dependencies",
            headers=headers,
            json={
                "source_task_id": source["id"],
                "target_task_id": target["id"],
                "dependency_type": "BLOCKS",
            },
        )
        assert response.status_code == 201

    schedule = (await client.get(f"/api/v1/projects/{project['id']}/schedule")).json()
    assert schedule["critical_path"]["project_duration_days"] == 9
    assert schedule["critical_path"]["critical_task_ids"] == [task["id"] for task in tasks]
    assert (
        await client.get(f"/api/v1/projects/{project['id']}/schedule/critical-path")
    ).status_code == 200
    baseline = await client.post(
        f"/api/v1/projects/{project['id']}/schedule/baseline", headers=headers, json={}
    )
    assert baseline.status_code == 201
    assert baseline.json()["task_count"] == 3
    assert (await client.get(f"/api/v1/projects/{project['id']}/schedule/baseline")).json()[
        "id"
    ] == baseline.json()["id"]
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/schedule/baseline", headers=headers, json={}
        )
    ).status_code == 409

    change = {
        "entity_type": "TASK",
        "task_id": tasks[0]["id"],
        "start_date": "2026-09-03",
        "due_date": "2026-09-05",
    }
    preview = (
        await client.post(
            f"/api/v1/projects/{project['id']}/schedule/preview", headers=headers, json=change
        )
    ).json()
    assert [item["projected_finish"] for item in preview["affected_tasks"]] == [
        "2026-09-05",
        "2026-09-08",
        "2026-09-11",
    ]
    assert preview["milestone_impacts"][0]["projected_date"] == "2026-09-11"
    assert preview["deadline_impact"] == {
        "projected_finish": "2026-09-11",
        "deadline": "2026-09-10",
        "variance_days": 1,
        "status": "LATE",
    }
    unchanged = (
        await client.get(f"/api/v1/projects/{project['id']}/tasks/{tasks[1]['id']}")
    ).json()
    assert unchanged["start_date"] == "2026-09-04"

    stale = preview
    await client.patch(
        f"/api/v1/projects/{project['id']}/tasks/{tasks[2]['id']}",
        headers=headers,
        json={"due_date": "2026-09-10"},
    )
    rejected = await client.post(
        f"/api/v1/projects/{project['id']}/schedule/apply",
        headers=headers,
        json={"preview_token": stale["preview_token"], "change": change},
    )
    assert rejected.status_code == 409
    preview = (
        await client.post(
            f"/api/v1/projects/{project['id']}/schedule/preview", headers=headers, json=change
        )
    ).json()
    applied = await client.post(
        f"/api/v1/projects/{project['id']}/schedule/apply",
        headers=headers,
        json={"preview_token": preview["preview_token"], "change": change},
    )
    assert applied.status_code == 200, applied.text
    final = applied.json()["schedule"]
    assert final["baseline_variance_days"] == 2
    final_by_id = {item["id"]: item for item in final["tasks"]}
    assert [final_by_id[task["id"]]["finish_variance"] for task in tasks] == [2, 2, 3]
    assert all(item["total_float"] == 0 for item in final["tasks"])
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/schedule/baseline",
            headers=headers,
            json={"replace": True},
        )
    ).status_code == 201
    await client.patch(
        f"/api/v1/projects/{project['id']}/tasks/{tasks[0]['id']}",
        headers=headers,
        json={"start_date": "2026-09-02", "due_date": "2026-09-04"},
    )
    earlier = (await client.get(f"/api/v1/projects/{project['id']}/schedule")).json()
    by_id = {item["id"]: item for item in earlier["tasks"]}
    assert by_id[tasks[0]["id"]]["start_variance"] == -1
    assert by_id[tasks[0]["id"]]["finish_variance"] == -1
    audit_rows = list(
        (await session.execute(select(AuditEvent.action, AuditEvent.actor_user_id))).all()
    )
    actions = {action for action, _actor in audit_rows}
    assert {
        "schedule.baseline_created",
        "schedule.baseline_replaced",
        "schedule.change_applied",
        "schedule.recursive_reschedule_applied",
    } <= actions
    assert all(actor == owner.id for action, actor in audit_rows if action.startswith("schedule."))

    recalculated = await client.post(
        f"/api/v1/projects/{project['id']}/intelligence/recalculate", headers=headers
    )
    assert recalculated.status_code == 200
    active_schedule_alerts = {
        item["title_key"]: item["id"]
        for item in recalculated.json()["alerts"]
        if item["rule_type"] == "advanced_schedule" and item["status"] != "RESOLVED"
    }
    assert "intelligence.alerts.scheduleProjectedLate.title" in active_schedule_alerts
    assert "intelligence.alerts.scheduleMilestoneLate.title" in active_schedule_alerts
    await client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={"target_end_date": "2026-10-15"},
    )
    await client.patch(
        f"/api/v1/projects/{project['id']}/milestones/{milestone['id']}",
        headers=headers,
        json={"due_date": "2026-10-01"},
    )
    reconciled = await client.post(
        f"/api/v1/projects/{project['id']}/intelligence/recalculate", headers=headers
    )
    by_alert_id = {item["id"]: item for item in reconciled.json()["alerts"]}
    assert all(
        by_alert_id[alert_id]["status"] == "RESOLVED"
        for alert_id in active_schedule_alerts.values()
    )

    viewer = await UserRepository(session).create(
        email="schedule-viewer@example.com", password_hash=hash_password(PASSWORD)
    )
    session.add(
        ProjectMembership(
            project_id=UUID(project["id"]),
            user_id=viewer.id,
            role=ProjectAccessRole.VIEWER,
            status=MembershipStatus.ACTIVE,
            created_by_user_id=owner.id,
        )
    )
    await session.commit()
    logged_in = await client.post(
        "/api/v1/auth/login", json={"email": viewer.email, "password": PASSWORD}
    )
    assert logged_in.status_code == 200
    viewer_headers = {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}
    assert (await client.get(f"/api/v1/projects/{project['id']}/schedule")).status_code == 200
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/schedule/preview",
            headers=viewer_headers,
            json=change,
        )
    ).status_code == 403
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/schedule/apply",
            headers=viewer_headers,
            json={"preview_token": preview["preview_token"], "change": change},
        )
    ).status_code == 403
