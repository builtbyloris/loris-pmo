from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password
from app.models.audit import AuditEvent
from app.repositories.users import UserRepository

PASSWORD = "a secure people sprint password"


async def login_as(client: AsyncClient, session: AsyncSession, email: str) -> dict[str, str]:
    await UserRepository(session).create(email=email, password_hash=hash_password(PASSWORD))
    await session.commit()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


async def create_project(client: AsyncClient, headers: dict[str, str], code: str) -> dict:
    response = await client.post(
        "/api/v1/projects",
        json={"name": f"Project {code}", "code": code},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_person(client: AsyncClient, headers: dict[str, str], name: str, **values) -> dict:
    response = await client.post("/api/v1/people", json={"name": name, **values}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def add_member(
    client: AsyncClient,
    headers: dict[str, str],
    project_id: str,
    person_id: str,
    **values,
) -> dict:
    response = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"person_id": person_id, **values},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_person_creation_validation_and_ownership_isolation(
    client: AsyncClient, session: AsyncSession
) -> None:
    owner = await login_as(client, session, "people-owner@example.com")
    person = await create_person(
        client,
        owner,
        "  Ada Lovelace  ",
        email="ada@example.com",
        department="Engineering",
        skills=["Python", "Python", " Planning "],
    )
    assert person["name"] == "Ada Lovelace"
    assert person["skills"] == ["Python", "Planning"]
    assert (await client.get("/api/v1/people")).json()[0]["id"] == person["id"]
    assert (
        await client.post("/api/v1/people", json={"name": "   "}, headers=owner)
    ).status_code == 422
    assert (
        await client.post(
            "/api/v1/people",
            json={"name": "Invalid email", "email": "not-an-email"},
            headers=owner,
        )
    ).status_code == 422

    other = await login_as(client, session, "people-other@example.com")
    assert (await client.get("/api/v1/people")).json() == []
    assert (
        await client.patch(
            f"/api/v1/people/{person['id']}", json={"name": "No access"}, headers=other
        )
    ).status_code == 404
    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert "person.created" in actions


async def test_membership_rules_updates_and_removal_preserve_person(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "members@example.com")
    project = await create_project(client, headers, "MEMBERS")
    person = await create_person(client, headers, "Grace Hopper")
    member = await add_member(
        client,
        headers,
        project["id"],
        person["id"],
        role="DEVELOPER",
        responsibilities="Delivery",
        availability_percent=80,
    )
    assert member["person"]["name"] == "Grace Hopper"
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"person_id": person["id"]},
            headers=headers,
        )
    ).status_code == 409
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"person_id": person["id"], "availability_percent": 101},
            headers=headers,
        )
    ).status_code == 422
    updated = await client.patch(
        f"/api/v1/projects/{project['id']}/members/{member['id']}",
        json={"role": "PROJECT_MANAGER", "availability_percent": 60},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "PROJECT_MANAGER"

    other = await login_as(client, session, "foreign-person@example.com")
    foreign = await create_person(client, other, "Foreign Person")
    await client.post(
        "/api/v1/auth/login", json={"email": "members@example.com", "password": PASSWORD}
    )
    owner_headers = {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"person_id": foreign["id"]},
            headers=owner_headers,
        )
    ).status_code == 422
    assigned_task = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Membership cleanup", "assignee_ids": [member["id"]]},
        headers=owner_headers,
    )
    assert assigned_task.status_code == 201
    assert (
        await client.delete(
            f"/api/v1/projects/{project['id']}/members/{member['id']}",
            headers=owner_headers,
        )
    ).status_code == 204
    refreshed_task = await client.get(
        f"/api/v1/projects/{project['id']}/tasks/{assigned_task.json()['id']}"
    )
    assert refreshed_task.status_code == 200
    assert refreshed_task.json()["assignee_ids"] == []
    assignment_events = list(
        (
            await session.execute(
                select(AuditEvent).where(AuditEvent.action == "task.assignee_changed")
            )
        ).scalars()
    )
    assert any(
        event.changes.get("reason") == "project_member.removed"
        for event in assignment_events
    )
    people = (await client.get("/api/v1/people")).json()
    assert any(item["id"] == person["id"] for item in people)


async def test_task_assignments_validate_membership_project_and_audit(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "assignments@example.com")
    first = await create_project(client, headers, "ASSIGN-ONE")
    second = await create_project(client, headers, "ASSIGN-TWO")
    person = await create_person(client, headers, "Assigned Member")
    member = await add_member(client, headers, first["id"], person["id"])
    other_member = await add_member(client, headers, second["id"], person["id"])
    created = await client.post(
        f"/api/v1/projects/{first['id']}/tasks",
        json={"title": "Assigned task", "assignee_ids": [member["id"]]},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["assignee_ids"] == [member["id"]]
    assert (
        await client.patch(
            f"/api/v1/projects/{first['id']}/tasks/{task['id']}",
            json={"assignee_ids": [other_member["id"]]},
            headers=headers,
        )
    ).status_code == 422
    cleared = await client.patch(
        f"/api/v1/projects/{first['id']}/tasks/{task['id']}",
        json={"assignee_ids": []},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["assignee_ids"] == []
    actions = list((await session.execute(select(AuditEvent.action))).scalars())
    assert actions.count("task.assignee_changed") == 2


async def test_stakeholder_crud_matrix_values_and_ownership(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "stakeholders@example.com")
    project = await create_project(client, headers, "STAKEHOLDERS")
    person = await create_person(client, headers, "Known Sponsor")
    standalone = await client.post(
        f"/api/v1/projects/{project['id']}/stakeholders",
        json={
            "name": "External regulator",
            "organization": "Authority",
            "influence": "HIGH",
            "interest": "LOW",
            "communication_frequency": "Monthly",
        },
        headers=headers,
    )
    assert standalone.status_code == 201
    linked = await client.post(
        f"/api/v1/projects/{project['id']}/stakeholders",
        json={"person_id": person["id"], "influence": "HIGH", "interest": "HIGH"},
        headers=headers,
    )
    assert linked.status_code == 201
    assert linked.json()["display_name"] == "Known Sponsor"
    updated = await client.patch(
        f"/api/v1/projects/{project['id']}/stakeholders/{standalone.json()['id']}",
        json={"interest": "MEDIUM", "communication_channel": "Email"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["interest"] == "MEDIUM"

    other = await login_as(client, session, "stakeholder-other@example.com")
    foreign = await create_person(client, other, "Foreign Stakeholder")
    await client.post(
        "/api/v1/auth/login", json={"email": "stakeholders@example.com", "password": PASSWORD}
    )
    owner_headers = {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/stakeholders",
            json={"person_id": foreign["id"]},
            headers=owner_headers,
        )
    ).status_code == 422
    assert (
        await client.delete(
            f"/api/v1/projects/{project['id']}/stakeholders/{standalone.json()['id']}",
            headers=owner_headers,
        )
    ).status_code == 204


async def test_workload_uses_real_assignments_effort_and_availability(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "workload@example.com")
    project = await create_project(client, headers, "WORKLOAD")
    first_person = await create_person(client, headers, "Busy Member")
    second_person = await create_person(client, headers, "Unassigned Member")
    busy = await add_member(
        client, headers, project["id"], first_person["id"], availability_percent=40
    )
    await add_member(client, headers, project["id"], second_person["id"])
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    soon = (date.today() + timedelta(days=5)).isoformat()
    for payload in (
        {
            "title": "Overdue",
            "due_date": yesterday,
            "estimated_effort": "5",
            "actual_effort": "2",
        },
        {"title": "Due soon without estimate", "due_date": soon},
    ):
        response = await client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={**payload, "assignee_ids": [busy["id"]]},
            headers=headers,
        )
        assert response.status_code == 201, response.text
    workload = (await client.get(f"/api/v1/projects/{project['id']}/workload")).json()
    busy_row = next(item for item in workload if item["member_id"] == busy["id"])
    assert busy_row["active_task_count"] == 2
    assert busy_row["overdue_task_count"] == 1
    assert busy_row["due_soon_task_count"] == 1
    assert busy_row["estimated_effort"] == "5.00"
    assert busy_row["actual_effort"] == "2.00"
    assert busy_row["effort_data_complete"] is False
    assert busy_row["workload_status"] == "HIGH"
    idle_row = next(item for item in workload if item["member_id"] != busy["id"])
    assert idle_row["workload_status"] == "NO_DATA"
    summary = (await client.get(f"/api/v1/projects/{project['id']}/people/summary")).json()
    assert summary == {"team_size": 2, "stakeholder_count": 0, "workload_warning_count": 1}


async def test_archived_project_rejects_people_domain_writes(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "people-archive@example.com")
    project = await create_project(client, headers, "PEOPLE-ARCHIVE")
    person = await create_person(client, headers, "Archive Member")
    member = await add_member(client, headers, project["id"], person["id"])
    await client.post(f"/api/v1/projects/{project['id']}/archive", headers=headers)
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/members/{member['id']}",
            json={"availability_percent": 50},
            headers=headers,
        )
    ).status_code == 409
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/stakeholders",
            json={"name": "Blocked"},
            headers=headers,
        )
    ).status_code == 409
