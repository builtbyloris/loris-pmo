from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context import ProjectContextBuilder
from app.auth.passwords import hash_password
from app.models.audit import AuditEvent
from app.models.collaboration import ProjectAccessRole, ProjectMembership
from app.repositories.users import UserRepository

PASSWORD = "a secure collaboration test password"


async def create_user(session: AsyncSession, email: str):
    user = await UserRepository(session).create(email=email, password_hash=hash_password(PASSWORD))
    await session.commit()
    return user


async def login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


async def setup_project(client: AsyncClient, session: AsyncSession):
    owner = await create_user(session, "owner-v2@example.com")
    viewer = await create_user(session, "viewer-v2@example.com")
    contributor = await create_user(session, "contributor-v2@example.com")
    manager = await create_user(session, "manager-v2@example.com")
    admin = await create_user(session, "admin-v2@example.com")
    headers = await login(client, owner.email)
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Shared project", "code": "SHARED-1", "planned_budget": "50000"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    project = response.json()
    for user, role in (
        (viewer, "VIEWER"),
        (contributor, "CONTRIBUTOR"),
        (manager, "PROJECT_MANAGER"),
        (admin, "PROJECT_ADMIN"),
    ):
        result = await client.post(
            f"/api/v1/projects/{project['id']}/collaborators",
            json={"email": user.email, "role": role},
            headers=headers,
        )
        assert result.status_code == 201, result.text
    return project, owner, viewer, contributor, manager, admin, headers


async def test_owner_membership_and_exact_email_collaborator_management(
    client: AsyncClient, session: AsyncSession
) -> None:
    project, owner, viewer, *_rest, owner_headers = await setup_project(client, session)
    memberships = list(
        (
            await session.scalars(
                select(ProjectMembership).where(ProjectMembership.project_id == UUID(project["id"]))
            )
        ).all()
    )
    owner_membership = next(item for item in memberships if item.user_id == owner.id)
    assert owner_membership.role == ProjectAccessRole.OWNER
    assert len(memberships) == 5
    missing = await client.post(
        f"/api/v1/projects/{project['id']}/collaborators",
        json={"email": "not-registered@example.com", "role": "VIEWER"},
        headers=owner_headers,
    )
    assert missing.status_code == 404
    owner_change = await client.patch(
        f"/api/v1/projects/{project['id']}/collaborators/{owner_membership.id}",
        json={"role": "VIEWER"},
        headers=owner_headers,
    )
    assert owner_change.status_code == 409
    await login(client, viewer.email)
    access = (await client.get(f"/api/v1/projects/{project['id']}/access")).json()
    assert access["role"] == "VIEWER"
    assert "project.read" in access["capabilities"]
    assert "finance.read" not in access["capabilities"]


async def test_role_matrix_finance_and_shared_portfolio(
    client: AsyncClient, session: AsyncSession
) -> None:
    project, _owner, viewer, contributor, manager, *_ = await setup_project(client, session)
    await login(client, viewer.email)
    listing = (await client.get("/api/v1/projects")).json()
    assert listing["total"] == 1
    assert listing["items"][0]["planned_budget"] is None
    detail = (await client.get(f"/api/v1/projects/{project['id']}")).json()
    assert detail["planned_budget"] is None
    kpis = (await client.get(f"/api/v1/projects/{project['id']}/kpis")).json()
    assert not (
        {"planned_budget", "actual_cost", "finance_status"} & {item["key"] for item in kpis}
    )
    health = (await client.get(f"/api/v1/projects/{project['id']}/health")).json()
    assert "budget" not in {item["key"] for item in health["dimensions"]}
    assert "budget_pressure" not in {item["key"] for item in health["drivers"]}
    denied_task = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Viewer write"},
        headers={"X-CSRF-Token": client.cookies.get("loris_csrf_token")},
    )
    assert denied_task.status_code == 403
    assert (await client.get(f"/api/v1/projects/{project['id']}/budget")).status_code == 403
    assert (await client.get(f"/api/v1/projects/{project['id']}/reports/budget")).status_code == 403
    assert (await client.get(f"/api/v1/projects/{project['id']}/activity")).status_code == 403

    contributor_headers = await login(client, contributor.email)
    task = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Contributor task"},
        headers=contributor_headers,
    )
    assert task.status_code == 201, task.text
    assert (await client.get(f"/api/v1/projects/{project['id']}/budget")).status_code == 403
    summary_report = await client.get(f"/api/v1/projects/{project['id']}/reports/project-summary")
    assert summary_report.status_code == 403
    assert (
        await client.get(f"/api/v1/projects/{project['id']}/exports/expenses/csv")
    ).status_code == 403

    await login(client, manager.email)
    budget = await client.get(f"/api/v1/projects/{project['id']}/budget")
    assert budget.status_code == 200
    assert budget.json()["planned_budget"] == "50000.00"
    manager_kpis = (await client.get(f"/api/v1/projects/{project['id']}/kpis")).json()
    assert "planned_budget" in {item["key"] for item in manager_kpis}
    assert (await client.get(f"/api/v1/projects/{project['id']}/activity")).status_code == 200
    assert (
        await client.get(f"/api/v1/projects/{project['id']}/reports/project-summary")
    ).status_code == 200


async def test_comments_notifications_recipient_isolation_and_audit_actor(
    client: AsyncClient, session: AsyncSession
) -> None:
    project, owner, viewer, contributor, *_rest, owner_headers = await setup_project(
        client, session
    )
    task_response = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Discuss this"},
        headers=owner_headers,
    )
    task = task_response.json()
    contributor_headers = await login(client, contributor.email)
    comment = await client.post(
        f"/api/v1/projects/{project['id']}/comments",
        json={"entity_type": "TASK", "entity_id": task["id"], "body": "  Ready for review.  "},
        headers=contributor_headers,
    )
    assert comment.status_code == 201, comment.text
    assert comment.json()["body"] == "Ready for review."
    assert comment.json()["can_edit"] is True
    updated = await client.patch(
        f"/api/v1/projects/{project['id']}/comments/{comment.json()['id']}",
        json={"body": "Updated review note."},
        headers=contributor_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["body"] == "Updated review note."
    cross_target = await client.post(
        f"/api/v1/projects/{project['id']}/comments",
        json={
            "entity_type": "TASK",
            "entity_id": "00000000-0000-0000-0000-000000000001",
            "body": "Invalid",
        },
        headers=contributor_headers,
    )
    assert cross_target.status_code == 404

    await login(client, viewer.email)
    notifications = (await client.get("/api/v1/notifications")).json()
    assert notifications["unread_count"] >= 2
    assert any(item["type"] == "COMMENT_ADDED" for item in notifications["items"])
    other_id = notifications["items"][0]["id"]
    await login(client, owner.email)
    assert (
        await client.patch(
            f"/api/v1/notifications/{other_id}/read",
            headers={"X-CSRF-Token": client.cookies.get("loris_csrf_token")},
        )
    ).status_code == 404
    activity = await client.get(f"/api/v1/projects/{project['id']}/activity")
    assert activity.status_code == 200
    comment_event = next(
        item for item in activity.json()["items"] if item["action"] == "comment.created"
    )
    assert comment_event["actor_email"] == contributor.email
    assert comment_event["summary"].endswith("comment created")
    events = list(
        (
            await session.scalars(select(AuditEvent).where(AuditEvent.action == "comment.created"))
        ).all()
    )
    assert events[-1].actor_user_id == contributor.id
    deleted = await client.delete(
        f"/api/v1/projects/{project['id']}/comments/{comment.json()['id']}",
        headers={"X-CSRF-Token": client.cookies.get("loris_csrf_token")},
    )
    assert deleted.status_code == 204
    remaining = await client.get(
        f"/api/v1/projects/{project['id']}/comments",
        params={"entity_type": "TASK", "entity_id": task["id"]},
    )
    assert remaining.status_code == 200
    assert remaining.json() == []


async def test_user_person_mapping_is_project_scoped(
    client: AsyncClient, session: AsyncSession
) -> None:
    project, _owner, viewer, *_rest, owner_headers = await setup_project(client, session)
    person = (
        await client.post("/api/v1/people", json={"name": "Mapped person"}, headers=owner_headers)
    ).json()
    operational = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"person_id": person["id"], "role": "TEAM_MEMBER"},
        headers=owner_headers,
    )
    assert operational.status_code == 201
    members = (await client.get(f"/api/v1/projects/{project['id']}/collaborators")).json()
    viewer_membership = next(item for item in members if item["user_id"] == str(viewer.id))
    mapped = await client.patch(
        f"/api/v1/projects/{project['id']}/collaborators/{viewer_membership['id']}",
        json={"person_id": person["id"]},
        headers=owner_headers,
    )
    assert mapped.status_code == 200
    assert mapped.json()["person_name"] == "Mapped person"


async def test_ai_context_and_confirmation_honor_role_permissions(
    client: AsyncClient, session: AsyncSession
) -> None:
    project, _owner, _viewer, contributor, *_ = await setup_project(client, session)
    context = await ProjectContextBuilder(session, contributor.id).build(
        UUID(project["id"]), "Explain the budget and expenses"
    )
    assert "finance" not in context.sections
    assert not any(key.startswith("budget:") for key in context.evidence)
    headers = await login(client, contributor.email)
    denied = await client.post(
        f"/api/v1/projects/{project['id']}/ai/meetings/00000000-0000-0000-0000-000000000001/proposals/00000000-0000-0000-0000-000000000002/confirm",
        headers=headers,
    )
    assert denied.status_code == 403


async def test_non_member_and_cross_project_membership_ids_are_rejected(
    client: AsyncClient, session: AsyncSession
) -> None:
    project, owner, *_rest, owner_headers = await setup_project(client, session)
    second = await client.post(
        "/api/v1/projects",
        json={"name": "Other project", "code": "OTHER-1"},
        headers=owner_headers,
    )
    assert second.status_code == 201, second.text
    other_task = await client.post(
        f"/api/v1/projects/{second.json()['id']}/tasks",
        json={"title": "Other project task"},
        headers=owner_headers,
    )
    assert other_task.status_code == 201, other_task.text
    cross_comment = await client.post(
        f"/api/v1/projects/{project['id']}/comments",
        json={
            "entity_type": "TASK",
            "entity_id": other_task.json()["id"],
            "body": "Must not cross project boundaries",
        },
        headers=owner_headers,
    )
    assert cross_comment.status_code == 404
    other_membership = await session.scalar(
        select(ProjectMembership).where(
            ProjectMembership.project_id == UUID(second.json()["id"]),
            ProjectMembership.user_id == owner.id,
        )
    )
    assert other_membership is not None
    rejected = await client.patch(
        f"/api/v1/projects/{project['id']}/collaborators/{other_membership.id}",
        json={"status": "DISABLED"},
        headers=owner_headers,
    )
    assert rejected.status_code == 404

    outsider = await create_user(session, "outsider-v2@example.com")
    await login(client, outsider.email)
    assert (await client.get(f"/api/v1/projects/{project['id']}")).status_code == 404


async def test_project_admin_cannot_manage_or_create_peer_admins(
    client: AsyncClient, session: AsyncSession
) -> None:
    project, _owner, _viewer, _contributor, manager, admin, *_ = await setup_project(
        client, session
    )
    memberships = list(
        (
            await session.scalars(
                select(ProjectMembership).where(ProjectMembership.project_id == UUID(project["id"]))
            )
        ).all()
    )
    manager_membership = next(item for item in memberships if item.user_id == manager.id)
    admin_membership = next(item for item in memberships if item.user_id == admin.id)
    headers = await login(client, admin.email)
    elevated = await client.patch(
        f"/api/v1/projects/{project['id']}/collaborators/{manager_membership.id}",
        json={"role": "PROJECT_ADMIN"},
        headers=headers,
    )
    assert elevated.status_code == 403
    removed = await client.delete(
        f"/api/v1/projects/{project['id']}/collaborators/{admin_membership.id}",
        headers=headers,
    )
    assert removed.status_code == 403
    new_admin = await create_user(session, "new-admin-v2@example.com")
    created = await client.post(
        f"/api/v1/projects/{project['id']}/collaborators",
        json={"email": new_admin.email, "role": "PROJECT_ADMIN"},
        headers=headers,
    )
    assert created.status_code == 403


async def test_finance_documents_are_not_visible_to_contributors(
    client: AsyncClient, session: AsyncSession
) -> None:
    project, owner, _viewer, contributor, *_rest, owner_headers = await setup_project(
        client, session
    )
    uploaded = await client.post(
        f"/api/v1/projects/{project['id']}/documents",
        data={"category": "FINANCE"},
        files={"file": ("costs.txt", b"Restricted financial source", "text/plain")},
        headers=owner_headers,
    )
    assert uploaded.status_code == 201, uploaded.text
    document_id = uploaded.json()["id"]

    await login(client, contributor.email)
    listing = await client.get(f"/api/v1/projects/{project['id']}/documents")
    assert listing.status_code == 200
    assert all(item["id"] != document_id for item in listing.json())
    assert (
        await client.get(f"/api/v1/projects/{project['id']}/documents/{document_id}/download")
    ).status_code == 403
    knowledge = await client.post(
        f"/api/v1/projects/{project['id']}/knowledge/query",
        json={"query": "Restricted financial source"},
    )
    assert knowledge.status_code == 200
    assert knowledge.json()["matches"] == []

    cleanup_headers = await login(client, owner.email)
    removed = await client.delete(
        f"/api/v1/projects/{project['id']}/documents/{document_id}",
        headers=cleanup_headers,
    )
    assert removed.status_code == 204


async def test_task_assignment_notifies_the_linked_application_user(
    client: AsyncClient, session: AsyncSession
) -> None:
    project, _owner, _viewer, contributor, *_rest, owner_headers = await setup_project(
        client, session
    )
    person = (
        await client.post(
            "/api/v1/people", json={"name": "Linked contributor"}, headers=owner_headers
        )
    ).json()
    operational = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"person_id": person["id"], "role": "TEAM_MEMBER"},
        headers=owner_headers,
    )
    assert operational.status_code == 201, operational.text
    memberships = (await client.get(f"/api/v1/projects/{project['id']}/collaborators")).json()
    contributor_membership = next(
        item for item in memberships if item["user_id"] == str(contributor.id)
    )
    linked = await client.patch(
        f"/api/v1/projects/{project['id']}/collaborators/{contributor_membership['id']}",
        json={"person_id": person["id"]},
        headers=owner_headers,
    )
    assert linked.status_code == 200, linked.text
    task = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={
            "title": "Assigned collaboration task",
            "assignee_ids": [operational.json()["id"]],
        },
        headers=owner_headers,
    )
    assert task.status_code == 201, task.text

    await login(client, contributor.email)
    notifications = (await client.get("/api/v1/notifications")).json()["items"]
    assigned = next(item for item in notifications if item["type"] == "TASK_ASSIGNED")
    assert assigned["entity_type"] == "TASK"
    assert assigned["entity_id"] == task.json()["id"]
