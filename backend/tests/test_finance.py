from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password
from app.models.audit import AuditEvent
from app.repositories.users import UserRepository

PASSWORD = "a secure finance sprint password"


async def login_as(client: AsyncClient, session: AsyncSession, email: str) -> dict[str, str]:
    await UserRepository(session).create(email=email, password_hash=hash_password(PASSWORD))
    await session.commit()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


async def create_project(
    client: AsyncClient,
    headers: dict[str, str],
    code: str,
    *,
    budget: str = "1000.00",
) -> dict:
    response = await client.post(
        "/api/v1/projects",
        json={"name": f"Project {code}", "code": code, "planned_budget": budget},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_category(
    client: AsyncClient,
    headers: dict[str, str],
    project_id: str,
    name: str,
    amount: str,
) -> dict:
    response = await client.post(
        f"/api/v1/projects/{project_id}/budget/categories",
        json={"name": name, "planned_amount": amount},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_expense(
    client: AsyncClient,
    headers: dict[str, str],
    project_id: str,
    description: str,
    amount: str,
    expense_status: str,
    **values,
) -> dict:
    response = await client.post(
        f"/api/v1/projects/{project_id}/expenses",
        json={
            "description": description,
            "amount": amount,
            "date": "2026-08-29",
            "status": expense_status,
            **values,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_budget_retrieval_update_validation_ownership_and_audit(
    client: AsyncClient, session: AsyncSession
) -> None:
    owner = await login_as(client, session, "finance-budget@example.com")
    project = await create_project(client, owner, "FIN-BUDGET")
    budget = (await client.get(f"/api/v1/projects/{project['id']}/budget")).json()
    assert budget["planned_budget"] == "1000.00"
    assert budget["total_category_allocation"] == "0"

    updated = await client.patch(
        f"/api/v1/projects/{project['id']}/budget",
        json={"planned_budget": "1250.00"},
        headers=owner,
    )
    assert updated.status_code == 200
    assert updated.json()["planned_budget"] == "1250.00"
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/budget",
            json={"planned_budget": "-1"},
            headers=owner,
        )
    ).status_code == 422

    other = await login_as(client, session, "finance-budget-other@example.com")
    assert (await client.get(f"/api/v1/projects/{project['id']}/budget")).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/budget",
            json={"planned_budget": "999"},
            headers=other,
        )
    ).status_code == 404
    actions = list((await session.execute(select(AuditEvent.action))).scalars())
    assert "budget.changed" in actions


async def test_category_crud_duplicates_allocations_and_history_protection(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "finance-categories@example.com")
    project = await create_project(client, headers, "FIN-CATS")
    development = await create_category(client, headers, project["id"], "Development", "800")
    travel = await create_category(client, headers, project["id"], "Travel", "400")
    budget = (await client.get(f"/api/v1/projects/{project['id']}/budget")).json()
    assert budget["total_category_allocation"] == "1200.00"
    assert budget["unallocated_budget"] == "-200.00"
    assert budget["allocation_exceeds_budget"] is True
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/budget/categories",
            json={"name": " development ", "planned_amount": "1"},
            headers=headers,
        )
    ).status_code == 409
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/budget/categories",
            json={"name": "Invalid", "planned_amount": "-1"},
            headers=headers,
        )
    ).status_code == 422
    updated = await client.patch(
        f"/api/v1/projects/{project['id']}/budget/categories/{travel['id']}",
        json={"name": "Business travel", "planned_amount": "300"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Business travel"

    await create_expense(
        client,
        headers,
        project["id"],
        "Historical item",
        "20",
        "PAID",
        budget_category_id=development["id"],
    )
    assert (
        await client.delete(
            f"/api/v1/projects/{project['id']}/budget/categories/{development['id']}",
            headers=headers,
        )
    ).status_code == 409
    assert (
        await client.delete(
            f"/api/v1/projects/{project['id']}/budget/categories/{travel['id']}",
            headers=headers,
        )
    ).status_code == 204
    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert {
        "budget_category.created",
        "budget_category.updated",
        "budget_category.removed",
    } <= actions


async def test_expense_relationship_validation_and_cross_project_protection(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "finance-links@example.com")
    first = await create_project(client, headers, "FIN-LINK-1")
    second = await create_project(client, headers, "FIN-LINK-2")
    category = await create_category(client, headers, second["id"], "External", "100")
    task = (
        await client.post(
            f"/api/v1/projects/{second['id']}/tasks",
            json={"title": "Foreign task"},
            headers=headers,
        )
    ).json()
    milestone = (
        await client.post(
            f"/api/v1/projects/{second['id']}/milestones",
            json={"title": "Foreign milestone"},
            headers=headers,
        )
    ).json()
    base = {
        "description": "Invalid link",
        "amount": "10",
        "date": "2026-08-29",
        "status": "PLANNED",
    }
    for field, value in (
        ("budget_category_id", category["id"]),
        ("task_id", task["id"]),
        ("milestone_id", milestone["id"]),
    ):
        response = await client.post(
            f"/api/v1/projects/{first['id']}/expenses",
            json={**base, field: value},
            headers=headers,
        )
        assert response.status_code == 422
    assert (
        await client.post(
            f"/api/v1/projects/{first['id']}/expenses",
            json={**base, "amount": "0"},
            headers=headers,
        )
    ).status_code == 422
    assert (
        await client.post(
            f"/api/v1/projects/{first['id']}/expenses",
            json={**base, "status": "APPROVED"},
            headers=headers,
        )
    ).status_code == 422


async def test_expense_updates_status_transitions_filters_sort_and_cancel(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "finance-expenses@example.com")
    project = await create_project(client, headers, "FIN-EXP")
    category = await create_category(client, headers, project["id"], "Equipment", "500")
    first = await create_expense(
        client,
        headers,
        project["id"],
        "Laptop purchase",
        "300",
        "PLANNED",
        budget_category_id=category["id"],
        supplier="Hardware House",
    )
    await create_expense(
        client,
        headers,
        project["id"],
        "Small cable",
        "20",
        "PAID",
        date="2026-08-28",
    )
    filtered = await client.get(
        f"/api/v1/projects/{project['id']}/expenses?search=laptop&status=PLANNED"
        f"&category_id={category['id']}"
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    sorted_list = (
        await client.get(
            f"/api/v1/projects/{project['id']}/expenses?sort_by=amount&sort_order=asc"
        )
    ).json()
    assert [item["amount"] for item in sorted_list["items"]] == ["20.00", "300.00"]
    updated = await client.patch(
        f"/api/v1/projects/{project['id']}/expenses/{first['id']}",
        json={"description": "Laptop commitment", "status": "PENDING"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "PENDING"
    cancelled = await client.post(
        f"/api/v1/projects/{project['id']}/expenses/{first['id']}/cancel",
        headers=headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/expenses/{first['id']}",
            json={"amount": "250"},
            headers=headers,
        )
    ).status_code == 409
    actions = list((await session.execute(select(AuditEvent.action))).scalars())
    assert "expense.updated" in actions
    assert "expense.status_changed" in actions
    assert "expense.cancelled" in actions


async def test_budget_analytics_formulas_categories_months_and_thresholds(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "finance-analytics@example.com")
    project = await create_project(client, headers, "FIN-ANALYTICS")
    development = await create_category(client, headers, project["id"], "Development", "600")
    await create_category(client, headers, project["id"], "Travel", "200")
    await create_expense(
        client, headers, project["id"], "Plan", "100", "PLANNED",
        budget_category_id=development["id"],
    )
    await create_expense(
        client, headers, project["id"], "Commit", "200", "PENDING",
        budget_category_id=development["id"],
    )
    await create_expense(
        client, headers, project["id"], "Actual", "300", "PAID",
        budget_category_id=development["id"],
    )
    await create_expense(
        client, headers, project["id"], "Uncategorized", "50", "PAID",
        date="2026-09-01",
    )
    await create_expense(
        client, headers, project["id"], "Cancelled", "900", "CANCELLED",
        budget_category_id=development["id"],
    )
    analytics = (await client.get(f"/api/v1/projects/{project['id']}/budget/analytics")).json()
    totals = analytics["totals"]
    assert totals == {
        "planned_budget": "1000.00",
        "actual_cost": "350.00",
        "committed_cost": "200.00",
        "planned_expense_cost": "100.00",
        "forecast": "650.00",
        "remaining_budget": "450.00",
        "actual_variance": "650.00",
        "budget_utilization": "55.00",
        "financial_status": "NORMAL",
    }
    category = next(
        item
        for item in analytics["categories"]
        if item["category_id"] == development["id"]
    )
    assert category["forecast"] == "600.00"
    assert category["remaining_budget"] == "100.00"
    assert category["budget_utilization"] == "83.33"
    assert category["financial_status"] == "WARNING"
    assert analytics["uncategorized"]["actual_cost"] == "50.00"
    assert analytics["uncategorized"]["budget_utilization"] is None
    assert analytics["monthly_trend"] == [
        {"month": "2026-08", "planned": "100.00", "committed": "200.00", "actual": "300.00"},
        {"month": "2026-09", "planned": "0.00", "committed": "0.00", "actual": "50.00"},
    ]


async def test_zero_budget_unavailable_and_critical_threshold(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "finance-threshold@example.com")
    zero = await create_project(client, headers, "FIN-ZERO", budget="0")
    await create_expense(client, headers, zero["id"], "No budget actual", "10", "PAID")
    zero_totals = (
        await client.get(f"/api/v1/projects/{zero['id']}/budget/analytics")
    ).json()["totals"]
    assert zero_totals["budget_utilization"] is None
    assert zero_totals["financial_status"] == "UNAVAILABLE"
    assert zero_totals["remaining_budget"] == "-10.00"

    critical = await create_project(client, headers, "FIN-CRIT", budget="100")
    await create_expense(client, headers, critical["id"], "Commitment", "91", "PENDING")
    critical_totals = (
        await client.get(f"/api/v1/projects/{critical['id']}/budget/analytics")
    ).json()["totals"]
    assert critical_totals["budget_utilization"] == "91.00"
    assert critical_totals["financial_status"] == "CRITICAL"


async def test_archived_project_rejects_finance_writes_and_foreign_owner_is_hidden(
    client: AsyncClient, session: AsyncSession
) -> None:
    owner = await login_as(client, session, "finance-archive@example.com")
    project = await create_project(client, owner, "FIN-ARCHIVE")
    expense = await create_expense(client, owner, project["id"], "Before archive", "10", "PAID")
    await client.post(f"/api/v1/projects/{project['id']}/archive", headers=owner)
    writes = [
        await client.patch(
            f"/api/v1/projects/{project['id']}/budget",
            json={"planned_budget": "200"},
            headers=owner,
        ),
        await client.post(
            f"/api/v1/projects/{project['id']}/budget/categories",
            json={"name": "Blocked", "planned_amount": "1"},
            headers=owner,
        ),
        await client.post(
            f"/api/v1/projects/{project['id']}/expenses",
            json={"description": "Blocked", "amount": "1", "date": "2026-08-29"},
            headers=owner,
        ),
        await client.post(
            f"/api/v1/projects/{project['id']}/expenses/{expense['id']}/cancel",
            headers=owner,
        ),
    ]
    assert all(response.status_code == 409 for response in writes)

    other = await login_as(client, session, "finance-archive-other@example.com")
    assert (
        await client.get(f"/api/v1/projects/{project['id']}/budget/analytics")
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/projects/{project['id']}/expenses")
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/expenses/{expense['id']}",
            json={"amount": "11"},
            headers=other,
        )
    ).status_code == 404
