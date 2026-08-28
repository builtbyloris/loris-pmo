from datetime import date, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password
from app.models.audit import AuditEvent
from app.repositories.users import UserRepository

PASSWORD = "a secure work planning password"


async def login_as(client: AsyncClient, session: AsyncSession, email: str) -> dict:
    await UserRepository(session).create(email=email, password_hash=hash_password(PASSWORD))
    await session.commit()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


async def create_project(
    client: AsyncClient, headers: dict, code: str, *, name: str = "Work Plan"
) -> dict:
    response = await client.post(
        "/api/v1/projects",
        json={"name": name, "code": code, "priority": "HIGH"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_task(client: AsyncClient, headers: dict, project_id: str, **values) -> dict:
    payload = {"title": "Plan the release", **values}
    response = await client.post(
        f"/api/v1/projects/{project_id}/tasks", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_milestone(client: AsyncClient, headers: dict, project_id: str, **values) -> dict:
    payload = {"title": "Release candidate", **values}
    response = await client.post(
        f"/api/v1/projects/{project_id}/milestones", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_task_creation_validation_and_done_normalization(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "task-create@example.com")
    project = await create_project(client, headers, "TASK-CREATE")
    task = await create_task(
        client,
        headers,
        project["id"],
        status="DONE",
        completion_percentage=22,
        start_date="2026-09-01",
        due_date="2026-09-30",
        estimated_effort="12.5",
    )
    assert task["completion_percentage"] == 100
    assert task["estimated_effort"] == "12.50"

    invalid_date = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Invalid", "start_date": "2026-10-01", "due_date": "2026-09-01"},
        headers=headers,
    )
    assert invalid_date.status_code == 422
    invalid_completion = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Invalid", "completion_percentage": 101},
        headers=headers,
    )
    assert invalid_completion.status_code == 422
    invalid_effort = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Invalid", "actual_effort": -1},
        headers=headers,
    )
    assert invalid_effort.status_code == 422


async def test_task_ownership_and_cross_project_links_are_rejected(
    client: AsyncClient, session: AsyncSession
) -> None:
    first_headers = await login_as(client, session, "task-owner@example.com")
    first = await create_project(client, first_headers, "OWNER-ONE")
    second = await create_project(client, first_headers, "OWNER-TWO")
    foreign_parent = await create_task(client, first_headers, second["id"])
    foreign_milestone = await create_milestone(client, first_headers, second["id"])

    bad_parent = await client.post(
        f"/api/v1/projects/{first['id']}/tasks",
        json={"title": "Bad parent", "parent_task_id": foreign_parent["id"]},
        headers=first_headers,
    )
    assert bad_parent.status_code == 422
    bad_milestone = await client.post(
        f"/api/v1/projects/{first['id']}/tasks",
        json={"title": "Bad milestone", "milestone_id": foreign_milestone["id"]},
        headers=first_headers,
    )
    assert bad_milestone.status_code == 422

    other_headers = await login_as(client, session, "task-other@example.com")
    assert (await client.get(f"/api/v1/projects/{first['id']}/tasks")).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/projects/{second['id']}/tasks/{foreign_parent['id']}",
            json={"title": "No access"},
            headers=other_headers,
        )
    ).status_code == 404


async def test_one_level_subtasks_prevent_self_parent_and_cycles(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "subtasks@example.com")
    project = await create_project(client, headers, "SUBTASKS")
    parent = await create_task(client, headers, project["id"], title="Parent")
    child = await create_task(
        client, headers, project["id"], title="Child", parent_task_id=parent["id"]
    )
    nested = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Too deep", "parent_task_id": child["id"]},
        headers=headers,
    )
    assert nested.status_code == 422
    self_parent = await client.patch(
        f"/api/v1/projects/{project['id']}/tasks/{parent['id']}",
        json={"parent_task_id": parent["id"]},
        headers=headers,
    )
    assert self_parent.status_code == 422
    cycle = await client.patch(
        f"/api/v1/projects/{project['id']}/tasks/{parent['id']}",
        json={"parent_task_id": child["id"]},
        headers=headers,
    )
    assert cycle.status_code == 422


async def test_task_listing_filters_search_sort_update_and_archive(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "task-list@example.com")
    project = await create_project(client, headers, "TASK-LIST")
    milestone = await create_milestone(client, headers, project["id"])
    alpha = await create_task(
        client,
        headers,
        project["id"],
        title="Alpha delivery",
        status="TODO",
        priority="CRITICAL",
        milestone_id=milestone["id"],
    )
    await create_task(
        client, headers, project["id"], title="Beta review", status="REVIEW", priority="LOW"
    )
    listing = (
        await client.get(f"/api/v1/projects/{project['id']}/tasks?sort_by=title&sort_order=asc")
    ).json()
    assert [item["title"] for item in listing["items"]] == ["Alpha delivery", "Beta review"]
    assert (await client.get(f"/api/v1/projects/{project['id']}/tasks?status=TODO")).json()[
        "total"
    ] == 1
    assert (await client.get(f"/api/v1/projects/{project['id']}/tasks?priority=LOW")).json()[
        "items"
    ][0]["title"] == "Beta review"
    assert (await client.get(f"/api/v1/projects/{project['id']}/tasks?search=alpha")).json()[
        "items"
    ][0]["id"] == alpha["id"]
    assert (
        await client.get(f"/api/v1/projects/{project['id']}/tasks?milestone_id={milestone['id']}")
    ).json()["total"] == 1

    updated = await client.patch(
        f"/api/v1/projects/{project['id']}/tasks/{alpha['id']}",
        json={"status": "DONE", "completion_percentage": 15},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["completion_percentage"] == 100
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/tasks/{alpha['id']}",
            json={"due_date": "2026-01-01", "start_date": "2026-02-01"},
            headers=headers,
        )
    ).status_code == 422
    archived = await client.post(
        f"/api/v1/projects/{project['id']}/tasks/{alpha['id']}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert (await client.get(f"/api/v1/projects/{project['id']}/tasks")).json()["total"] == 1
    assert (
        await client.get(f"/api/v1/projects/{project['id']}/tasks?include_archived=true")
    ).json()["total"] == 2
    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert "task.archived" in actions


async def test_dependencies_reject_duplicates_self_cross_project_and_cycles(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "dependencies@example.com")
    project = await create_project(client, headers, "DEPENDENCIES")
    other = await create_project(client, headers, "DEPENDENCIES-OTHER")
    first = await create_task(client, headers, project["id"], title="First")
    second = await create_task(client, headers, project["id"], title="Second")
    third = await create_task(client, headers, project["id"], title="Third")
    foreign = await create_task(client, headers, other["id"], title="Foreign")
    endpoint = f"/api/v1/projects/{project['id']}/task-dependencies"

    created = await client.post(
        endpoint,
        json={
            "source_task_id": first["id"],
            "target_task_id": second["id"],
            "dependency_type": "BLOCKS",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert (
        await client.post(
            endpoint,
            json={
                "source_task_id": first["id"],
                "target_task_id": second["id"],
                "dependency_type": "BLOCKS",
            },
            headers=headers,
        )
    ).status_code == 409
    assert (
        await client.post(
            endpoint,
            json={
                "source_task_id": second["id"],
                "target_task_id": first["id"],
                "dependency_type": "DEPENDS_ON",
            },
            headers=headers,
        )
    ).status_code == 409
    assert (
        await client.post(
            endpoint,
            json={
                "source_task_id": first["id"],
                "target_task_id": first["id"],
                "dependency_type": "DEPENDS_ON",
            },
            headers=headers,
        )
    ).status_code == 422
    assert (
        await client.post(
            endpoint,
            json={
                "source_task_id": first["id"],
                "target_task_id": foreign["id"],
                "dependency_type": "RELATED_TO",
            },
            headers=headers,
        )
    ).status_code == 422
    assert (
        await client.post(
            endpoint,
            json={
                "source_task_id": second["id"],
                "target_task_id": third["id"],
                "dependency_type": "BLOCKS",
            },
            headers=headers,
        )
    ).status_code == 201
    cycle = await client.post(
        endpoint,
        json={
            "source_task_id": third["id"],
            "target_task_id": first["id"],
            "dependency_type": "BLOCKS",
        },
        headers=headers,
    )
    assert cycle.status_code == 409
    dependencies = (await client.get(endpoint)).json()
    assert len(dependencies) == 2
    removed = await client.delete(f"{endpoint}/{created.json()['id']}", headers=headers)
    assert removed.status_code == 204
    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert {"dependency.created", "dependency.removed"} <= actions


async def test_milestone_progress_and_project_summary_are_deterministic(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "milestones@example.com")
    project = await create_project(client, headers, "MILESTONES")
    milestone = await create_milestone(
        client,
        headers,
        project["id"],
        due_date=(date.today() + timedelta(days=10)).isoformat(),
    )
    assert milestone["progress"] is None
    await create_task(
        client,
        headers,
        project["id"],
        title="Twenty percent",
        milestone_id=milestone["id"],
        completion_percentage=20,
        due_date=(date.today() - timedelta(days=1)).isoformat(),
    )
    await create_task(
        client,
        headers,
        project["id"],
        title="Complete",
        milestone_id=milestone["id"],
        status="DONE",
    )
    await create_task(
        client,
        headers,
        project["id"],
        title="Excluded cancellation",
        milestone_id=milestone["id"],
        status="CANCELLED",
    )
    milestones = (await client.get(f"/api/v1/projects/{project['id']}/milestones")).json()
    assert milestones[0]["progress"] == 60.0
    assert milestones[0]["linked_task_count"] == 2
    assert milestones[0]["overdue_task_count"] == 1
    summary = (await client.get(f"/api/v1/projects/{project['id']}/work-planning/summary")).json()
    assert summary["total_tasks"] == 3
    assert summary["completed_tasks"] == 1
    assert summary["overdue_tasks"] == 1
    assert summary["upcoming_milestones"] == 1
    assert summary["progress"] == 60.0

    completed = await client.patch(
        f"/api/v1/projects/{project['id']}/milestones/{milestone['id']}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert completed.status_code == 200


async def test_archived_project_is_read_only_and_operations_are_audited(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "planning-archive@example.com")
    project = await create_project(client, headers, "PLANNING-ARCHIVE")
    task = await create_task(client, headers, project["id"])
    milestone = await create_milestone(client, headers, project["id"])
    await client.patch(
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    await client.patch(
        f"/api/v1/projects/{project['id']}/milestones/{milestone['id']}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    await client.post(f"/api/v1/projects/{project['id']}/archive", headers=headers)
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"title": "Blocked"},
            headers=headers,
        )
    ).status_code == 409
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/milestones",
            json={"title": "Blocked"},
            headers=headers,
        )
    ).status_code == 409

    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert {
        "task.created",
        "task.updated",
        "task.status_changed",
        "milestone.created",
        "milestone.updated",
        "milestone.completed",
    } <= actions


async def test_unknown_and_unauthenticated_work_planning_access_is_rejected(
    client: AsyncClient,
) -> None:
    project_id = uuid4()
    assert (await client.get(f"/api/v1/projects/{project_id}/tasks")).status_code == 401
