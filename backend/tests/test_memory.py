from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password
from app.models.audit import AuditEvent
from app.models.memory import ProjectLogEntry
from app.repositories.users import UserRepository

PASSWORD = "a secure project memory password"


async def setup(client: AsyncClient, session: AsyncSession, suffix: str):
    await UserRepository(session).create(
        email=f"memory-{suffix}@example.com", password_hash=hash_password(PASSWORD)
    )
    await session.commit()
    await client.post(
        "/api/v1/auth/login",
        json={"email": f"memory-{suffix}@example.com", "password": PASSWORD},
    )
    headers = {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}
    project = (
        await client.post(
            "/api/v1/projects",
            json={"name": f"Memory {suffix}", "code": f"MEM-{suffix}"},
            headers=headers,
        )
    ).json()
    person = (
        await client.post("/api/v1/people", json={"name": "Memory Owner"}, headers=headers)
    ).json()
    member = (
        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"person_id": person["id"], "role": "PROJECT_MANAGER"},
            headers=headers,
        )
    ).json()
    return headers, project, member


async def test_manual_log_links_search_and_cross_project_protection(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, project, _ = await setup(client, session, "LOG")
    task = (
        await client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"title": "Linked task"},
            headers=headers,
        )
    ).json()
    created = await client.post(
        f"/api/v1/projects/{project['id']}/log",
        json={
            "type": "NOTE",
            "title": "Architecture context",
            "description": "Persistent project memory",
            "links": [{"entity_type": "TASK", "entity_id": task["id"]}],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["links"][0]["entity_name"] == "Linked task"
    listing = await client.get(
        f"/api/v1/projects/{project['id']}/log?search=architecture&type=NOTE"
    )
    assert listing.json()["total"] == 1

    other = (
        await client.post(
            "/api/v1/projects",
            json={"name": "Other", "code": "MEM-LOG-OTHER"},
            headers=headers,
        )
    ).json()
    foreign = (
        await client.post(
            f"/api/v1/projects/{other['id']}/tasks",
            json={"title": "Foreign"},
            headers=headers,
        )
    ).json()
    invalid = await client.post(
        f"/api/v1/projects/{project['id']}/log",
        json={
            "title": "Invalid",
            "links": [{"entity_type": "TASK", "entity_id": foreign["id"]}],
        },
        headers=headers,
    )
    assert invalid.status_code == 422


async def test_meeting_participants_action_review_and_completion_memory(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, project, member = await setup(client, session, "MEET")
    naive_schedule = await client.post(
        f"/api/v1/projects/{project['id']}/meetings",
        json={"title": "Missing timezone", "scheduled_at": "2026-09-01T09:00:00"},
        headers=headers,
    )
    assert naive_schedule.status_code == 422
    meeting_response = await client.post(
        f"/api/v1/projects/{project['id']}/meetings",
        json={
            "title": "Steering review",
            "scheduled_at": "2026-09-01T09:00:00Z",
            "duration_minutes": 45,
            "agenda": "Delivery decisions",
            "participant_ids": [member["id"]],
        },
        headers=headers,
    )
    assert meeting_response.status_code == 201, meeting_response.text
    meeting = meeting_response.json()
    assert meeting["participant_ids"] == [member["id"]]
    action = (
        await client.post(
            f"/api/v1/projects/{project['id']}/meetings/{meeting['id']}/action-items",
            json={
                "description": "Prepare rollout plan",
                "owner_member_id": member["id"],
                "due_date": "2026-09-05",
            },
            headers=headers,
        )
    ).json()
    assert action["status"] == "PROPOSED"
    confirmed = await client.patch(
        f"/api/v1/projects/{project['id']}/meetings/{meeting['id']}/action-items/{action['id']}",
        json={"status": "CONFIRMED"},
        headers=headers,
    )
    assert confirmed.json()["status"] == "CONFIRMED"
    invalid = await client.patch(
        f"/api/v1/projects/{project['id']}/meetings/{meeting['id']}/action-items/{action['id']}",
        json={"status": "PROPOSED"},
        headers=headers,
    )
    assert invalid.status_code == 409
    completed = await client.patch(
        f"/api/v1/projects/{project['id']}/meetings/{meeting['id']}",
        json={"status": "COMPLETED", "notes": "Actions reviewed"},
        headers=headers,
    )
    assert completed.json()["status"] == "COMPLETED"
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/meetings/{meeting['id']}",
            json={"scheduled_at": None},
            headers=headers,
        )
    ).status_code == 422
    logs = (await client.get(f"/api/v1/projects/{project['id']}/log")).json()["items"]
    automatic = next(item for item in logs if item["type"] == "MEETING")
    assert automatic["source"] == "SYSTEM"
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/log/{automatic['id']}",
            json={"title": "Rewrite history"},
            headers=headers,
        )
    ).status_code == 409


async def test_decision_history_links_activity_and_summary(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, project, member = await setup(client, session, "DEC")
    task = (
        await client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"title": "Decision work"},
            headers=headers,
        )
    ).json()
    response = await client.post(
        f"/api/v1/projects/{project['id']}/decisions",
        json={
            "title": "Release strategy",
            "decision": "Use a phased rollout",
            "decision_date": "2026-09-01",
            "decision_maker_member_id": member["id"],
            "reason": "Reduce delivery risk",
            "status": "PROPOSED",
            "links": [{"entity_type": "TASK", "entity_id": task["id"]}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    decision = response.json()
    assert decision["links"][0]["entity_name"] == "Decision work"
    decided = await client.patch(
        f"/api/v1/projects/{project['id']}/decisions/{decision['id']}",
        json={"status": "DECIDED", "expected_impact": "Safer launch"},
        headers=headers,
    )
    assert decided.json()["status"] == "DECIDED"
    reversed_response = await client.patch(
        f"/api/v1/projects/{project['id']}/decisions/{decision['id']}",
        json={"status": "REVERSED", "actual_impact": "Market conditions changed"},
        headers=headers,
    )
    assert reversed_response.json()["status"] == "REVERSED"
    assert (
        await client.delete(
            f"/api/v1/projects/{project['id']}/decisions/{decision['id']}", headers=headers
        )
    ).status_code == 405
    activity = (
        await client.get(f"/api/v1/projects/{project['id']}/activity?search=decision")
    ).json()
    assert activity["total"] >= 2
    assert any(item["entity_name"] == "Release strategy" for item in activity["items"])
    summary = (await client.get(f"/api/v1/projects/{project['id']}/memory/summary")).json()
    assert summary["recent_decisions"][0]["title"] == "Release strategy"
    assert any(item["status"] == "DECISION" for item in summary["recent_log_entries"])


async def test_only_meaningful_control_and_milestone_events_enter_project_log(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, project, _ = await setup(client, session, "AUTO")
    milestone = (
        await client.post(
            f"/api/v1/projects/{project['id']}/milestones",
            json={"title": "Launch"},
            headers=headers,
        )
    ).json()
    await client.patch(
        f"/api/v1/projects/{project['id']}/milestones/{milestone['id']}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    risk = (
        await client.post(
            f"/api/v1/projects/{project['id']}/risks",
            json={
                "title": "Vendor",
                "probability": 2,
                "impact": 2,
                "identified_date": "2026-09-01",
            },
            headers=headers,
        )
    ).json()
    await client.post(f"/api/v1/projects/{project['id']}/risks/{risk['id']}/close", headers=headers)
    issue = (
        await client.post(
            f"/api/v1/projects/{project['id']}/issues",
            json={"title": "Delay", "identified_date": "2026-09-01"},
            headers=headers,
        )
    ).json()
    await client.post(
        f"/api/v1/projects/{project['id']}/issues/{issue['id']}/resolve",
        json={"resolution": "Recovered"},
        headers=headers,
    )
    change = (
        await client.post(
            f"/api/v1/projects/{project['id']}/changes",
            json={"title": "Scope", "requested_date": "2026-09-01"},
            headers=headers,
        )
    ).json()
    await client.post(
        f"/api/v1/projects/{project['id']}/changes/{change['id']}/submit", headers=headers
    )
    await client.post(
        f"/api/v1/projects/{project['id']}/changes/{change['id']}/approve",
        json={"decision": "Approved"},
        headers=headers,
    )
    logs = list((await session.execute(select(ProjectLogEntry))).scalars())
    assert {item.type.value for item in logs} == {"MILESTONE", "RISK_UPDATE", "ISSUE", "CHANGE"}
    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert {
        "milestone.completed",
        "risk.closed",
        "issue.resolved",
        "change_request.approved",
    } <= actions
