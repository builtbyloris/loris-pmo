from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password
from app.models.audit import AuditEvent
from app.repositories.users import UserRepository

PASSWORD = "a secure projects test password"


async def login_as(client: AsyncClient, session: AsyncSession, email: str):
    user = await UserRepository(session).create(email=email, password_hash=hash_password(PASSWORD))
    await session.commit()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return user, {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


def project_payload(**overrides) -> dict:
    data = {
        "name": "Platform Launch",
        "code": "PLAT-01",
        "description": "Launch the project platform.",
        "client_or_area": "Digital Operations",
        "priority": "HIGH",
        "start_date": "2026-09-01",
        "target_end_date": "2026-12-15",
        "planned_budget": "125000.00",
    }
    data.update(overrides)
    return data


async def create_project(client: AsyncClient, headers: dict, **overrides) -> dict:
    response = await client.post(
        "/api/v1/projects", json=project_payload(**overrides), headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_authenticated_user_creates_project_with_children_and_audit(
    client: AsyncClient, session: AsyncSession
) -> None:
    _user, headers = await login_as(client, session, "owner@example.com")
    response = await client.post(
        "/api/v1/projects",
        json=project_payload(
            code=" plat-01 ",
            objectives=[{"title": "Deliver the launch"}],
            success_criteria=[{"description": "Launch before year end"}],
        ),
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "PLAT-01"
    assert body["objectives"][0]["title"] == "Deliver the launch"
    assert body["success_criteria"][0]["description"] == "Launch before year end"
    assert (await session.execute(select(func.count(AuditEvent.id)))).scalar_one() == 3


async def test_unauthenticated_creation_is_rejected(client: AsyncClient) -> None:
    response = await client.post("/api/v1/projects", json=project_payload())
    assert response.status_code == 401


async def test_project_validation_rejects_dates_budget_and_unknown_enum(
    client: AsyncClient, session: AsyncSession
) -> None:
    _user, headers = await login_as(client, session, "validation@example.com")
    invalid_date = await client.post(
        "/api/v1/projects",
        json=project_payload(start_date="2026-12-01", target_end_date="2026-10-01"),
        headers=headers,
    )
    assert invalid_date.status_code == 422
    negative_budget = await client.post(
        "/api/v1/projects", json=project_payload(planned_budget="-1"), headers=headers
    )
    assert negative_budget.status_code == 422
    unknown_priority = await client.post(
        "/api/v1/projects", json=project_payload(priority="URGENT"), headers=headers
    )
    assert unknown_priority.status_code == 422


async def test_project_ownership_hides_retrieve_and_update(
    client: AsyncClient, session: AsyncSession
) -> None:
    _owner, owner_headers = await login_as(client, session, "first@example.com")
    project = await create_project(client, owner_headers)
    _other, other_headers = await login_as(client, session, "second@example.com")
    assert (await client.get(f"/api/v1/projects/{project['id']}")).status_code == 404
    update = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"name": "Stolen"}, headers=other_headers
    )
    assert update.status_code == 404


async def test_listing_is_owner_scoped_and_filters_search_and_sort_work(
    client: AsyncClient, session: AsyncSession
) -> None:
    _first, first_headers = await login_as(client, session, "list@example.com")
    await create_project(
        client, first_headers, code="ALPHA-1", name="Alpha Launch", status="ACTIVE"
    )
    await create_project(
        client,
        first_headers,
        code="BETA-1",
        name="Beta Migration",
        status="ON_HOLD",
        priority="CRITICAL",
    )
    _second, second_headers = await login_as(client, session, "other-list@example.com")
    await create_project(client, second_headers, code="OTHER-1", name="Other User Project")
    await client.post(
        "/api/v1/auth/login", json={"email": "list@example.com", "password": PASSWORD}
    )

    listing = (await client.get("/api/v1/projects?sort_by=name&sort_order=asc")).json()
    assert listing["total"] == 2
    assert [item["code"] for item in listing["items"]] == ["ALPHA-1", "BETA-1"]
    assert (await client.get("/api/v1/projects?status=ACTIVE")).json()["total"] == 1
    assert (await client.get("/api/v1/projects?priority=CRITICAL")).json()["items"][0][
        "code"
    ] == "BETA-1"
    assert (await client.get("/api/v1/projects?search=migration")).json()["items"][0][
        "code"
    ] == "BETA-1"


async def test_valid_update_and_invalid_partial_date_update(
    client: AsyncClient, session: AsyncSession
) -> None:
    _user, headers = await login_as(client, session, "update@example.com")
    project = await create_project(client, headers)
    updated = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Platform Launch 2", "status": "ACTIVE", "planned_budget": "130000"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Platform Launch 2"
    invalid = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"target_end_date": "2026-08-01"},
        headers=headers,
    )
    assert invalid.status_code == 422

    required_null = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"name": None}, headers=headers
    )
    assert required_null.status_code == 422


async def test_archive_excludes_default_list_and_includes_archive_filter(
    client: AsyncClient, session: AsyncSession
) -> None:
    _user, headers = await login_as(client, session, "archive@example.com")
    project = await create_project(client, headers)
    archived = await client.post(f"/api/v1/projects/{project['id']}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    assert archived.json()["archived_at"] is not None
    assert (await client.get("/api/v1/projects")).json()["total"] == 0
    included = (await client.get("/api/v1/projects?include_archived=true&status=ARCHIVED")).json()
    assert included["total"] == 1
    assert included["items"][0]["id"] == project["id"]


async def test_objective_and_criterion_crud_validate_relationship_and_ownership(
    client: AsyncClient, session: AsyncSession
) -> None:
    _owner, headers = await login_as(client, session, "children@example.com")
    project = await create_project(client, headers)
    objective_response = await client.post(
        f"/api/v1/projects/{project['id']}/objectives",
        json={"title": "Launch successfully"},
        headers=headers,
    )
    assert objective_response.status_code == 201
    objective = objective_response.json()
    criterion_response = await client.post(
        f"/api/v1/projects/{project['id']}/success-criteria",
        json={"description": "Release before December", "objective_id": objective["id"]},
        headers=headers,
    )
    assert criterion_response.status_code == 201
    criterion = criterion_response.json()
    assert criterion["objective_id"] == objective["id"]
    patched = await client.patch(
        f"/api/v1/projects/{project['id']}/objectives/{objective['id']}",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert patched.status_code == 200
    bad_relationship = await client.post(
        f"/api/v1/projects/{project['id']}/success-criteria",
        json={"description": "Invalid", "objective_id": str(uuid4())},
        headers=headers,
    )
    assert bad_relationship.status_code == 422

    _other, other_headers = await login_as(client, session, "children-other@example.com")
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/objectives/{objective['id']}",
            json={"title": "No access"},
            headers=other_headers,
        )
    ).status_code == 404
    assert (
        await client.delete(
            f"/api/v1/projects/{project['id']}/success-criteria/{criterion['id']}",
            headers=other_headers,
        )
    ).status_code == 404

    await client.post(
        "/api/v1/auth/login", json={"email": "children@example.com", "password": PASSWORD}
    )
    owner_headers = {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}
    assert (
        await client.delete(
            f"/api/v1/projects/{project['id']}/success-criteria/{criterion['id']}",
            headers=owner_headers,
        )
    ).status_code == 204
    preserved_criterion = (
        await client.post(
            f"/api/v1/projects/{project['id']}/success-criteria",
            json={
                "description": "Remain after objective deletion",
                "objective_id": objective["id"],
            },
            headers=owner_headers,
        )
    ).json()
    assert (
        await client.delete(
            f"/api/v1/projects/{project['id']}/objectives/{objective['id']}",
            headers=owner_headers,
        )
    ).status_code == 204
    detail = (await client.get(f"/api/v1/projects/{project['id']}")).json()
    assert (
        next(
            item for item in detail["success_criteria"] if item["id"] == preserved_criterion["id"]
        )["objective_id"]
        is None
    )


async def test_nested_criterion_cannot_link_to_another_projects_objective(
    client: AsyncClient, session: AsyncSession
) -> None:
    _user, headers = await login_as(client, session, "nested-relation@example.com")
    existing = await create_project(client, headers, code="EXISTING")
    objective = (
        await client.post(
            f"/api/v1/projects/{existing['id']}/objectives",
            json={"title": "Existing objective"},
            headers=headers,
        )
    ).json()

    response = await client.post(
        "/api/v1/projects",
        json=project_payload(
            code="NEW-PROJECT",
            success_criteria=[
                {
                    "description": "Must not cross-link",
                    "objective_id": objective["id"],
                }
            ],
        ),
        headers=headers,
    )
    assert response.status_code == 422


async def test_portfolio_uses_only_real_project_status_counts(
    client: AsyncClient, session: AsyncSession
) -> None:
    _user, headers = await login_as(client, session, "portfolio@example.com")
    empty = (await client.get("/api/v1/portfolio/summary")).json()
    assert empty == {
        "total_projects": 0,
        "active_projects": 0,
        "on_hold_projects": 0,
        "completed_projects": 0,
    }
    await create_project(client, headers, code="ACTIVE-1", status="ACTIVE")
    await create_project(client, headers, code="HOLD-1", status="ON_HOLD")
    await create_project(client, headers, code="DONE-1", status="COMPLETED")
    summary = (await client.get("/api/v1/portfolio/summary")).json()
    assert summary == {
        "total_projects": 3,
        "active_projects": 1,
        "on_hold_projects": 1,
        "completed_projects": 1,
    }
