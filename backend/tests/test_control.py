from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.control import RiskSeverity, risk_score, risk_severity
from app.auth.passwords import hash_password
from app.models.audit import AuditEvent
from app.repositories.users import UserRepository

PASSWORD = "a secure control sprint password"


async def login_as(client: AsyncClient, session: AsyncSession, email: str) -> dict[str, str]:
    await UserRepository(session).create(email=email, password_hash=hash_password(PASSWORD))
    await session.commit()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


async def create_project(client: AsyncClient, headers: dict[str, str], code: str) -> dict:
    response = await client.post(
        "/api/v1/projects",
        json={"name": f"Control {code}", "code": code, "planned_budget": "2000"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def add_member(
    client: AsyncClient, headers: dict[str, str], project_id: str, name: str
) -> dict:
    person_response = await client.post("/api/v1/people", json={"name": name}, headers=headers)
    assert person_response.status_code == 201, person_response.text
    response = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"person_id": person_response.json()["id"], "role": "PROJECT_MANAGER"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_risk(
    client: AsyncClient, headers: dict[str, str], project_id: str, title: str, **values
) -> dict:
    response = await client.post(
        f"/api/v1/projects/{project_id}/risks",
        json={
            "title": title,
            "probability": 3,
            "impact": 4,
            "identified_date": "2026-08-29",
            **values,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_issue(
    client: AsyncClient, headers: dict[str, str], project_id: str, title: str, **values
) -> dict:
    response = await client.post(
        f"/api/v1/projects/{project_id}/issues",
        json={"title": title, "identified_date": "2026-08-29", **values},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_change(
    client: AsyncClient, headers: dict[str, str], project_id: str, title: str, **values
) -> dict:
    response = await client.post(
        f"/api/v1/projects/{project_id}/changes",
        json={"title": title, "requested_date": "2026-08-29", **values},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_risk_score_and_severity_bands() -> None:
    assert risk_score(1, 1) == 1
    assert risk_score(5, 5) == 25
    assert risk_severity(4) == RiskSeverity.LOW
    assert risk_severity(5) == RiskSeverity.MEDIUM
    assert risk_severity(9) == RiskSeverity.MEDIUM
    assert risk_severity(10) == RiskSeverity.HIGH
    assert risk_severity(16) == RiskSeverity.HIGH
    assert risk_severity(17) == RiskSeverity.CRITICAL
    assert risk_severity(25) == RiskSeverity.CRITICAL


async def test_risk_crud_matrix_filters_links_owner_and_audits(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "control-risks@example.com")
    project = await create_project(client, headers, "CTRL-RISK")
    other = await create_project(client, headers, "CTRL-RISK-OTHER")
    member = await add_member(client, headers, project["id"], "Risk Owner")
    task = (
        await client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"title": "Mitigation task"},
            headers=headers,
        )
    ).json()
    milestone = (
        await client.post(
            f"/api/v1/projects/{project['id']}/milestones",
            json={"title": "Risk checkpoint"},
            headers=headers,
        )
    ).json()
    risk = await create_risk(
        client,
        headers,
        project["id"],
        "Critical supplier risk",
        probability=5,
        impact=4,
        owner_member_id=member["id"],
        task_ids=[task["id"]],
        milestone_ids=[milestone["id"]],
    )
    assert (risk["risk_score"], risk["severity"]) == (20, "CRITICAL")
    assert risk["task_ids"] == [task["id"]]
    protected_member = await client.delete(
        f"/api/v1/projects/{project['id']}/members/{member['id']}", headers=headers
    )
    assert protected_member.status_code == 409
    listing = await client.get(
        f"/api/v1/projects/{project['id']}/risks?severity=CRITICAL&search=supplier"
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    updated = await client.patch(
        f"/api/v1/projects/{project['id']}/risks/{risk['id']}",
        json={"probability": 2, "impact": 2, "status": "MONITORING"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert (updated.json()["risk_score"], updated.json()["severity"]) == (4, "LOW")

    foreign_task = (
        await client.post(
            f"/api/v1/projects/{other['id']}/tasks",
            json={"title": "Foreign"},
            headers=headers,
        )
    ).json()
    invalid = await client.patch(
        f"/api/v1/projects/{project['id']}/risks/{risk['id']}",
        json={"task_ids": [foreign_task["id"]]},
        headers=headers,
    )
    assert invalid.status_code == 422
    closed = await client.post(
        f"/api/v1/projects/{project['id']}/risks/{risk['id']}/close", headers=headers
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/risks/{risk['id']}",
            json={"title": "Locked"},
            headers=headers,
        )
    ).status_code == 409
    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert {"risk.created", "risk.updated", "risk.severity_changed", "risk.closed"} <= actions


async def test_issue_workflow_resolution_links_and_summary(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "control-issues@example.com")
    project = await create_project(client, headers, "CTRL-ISSUE")
    task = (
        await client.post(
            f"/api/v1/projects/{project['id']}/tasks", json={"title": "Recovery"}, headers=headers
        )
    ).json()
    issue = await create_issue(
        client,
        headers,
        project["id"],
        "Production outage",
        priority="CRITICAL",
        schedule_impact="HIGH",
        estimated_delay_days=3,
        task_ids=[task["id"]],
    )
    assert issue["status"] == "OPEN"
    invalid = await client.patch(
        f"/api/v1/projects/{project['id']}/issues/{issue['id']}",
        json={"status": "RESOLVED"},
        headers=headers,
    )
    assert invalid.status_code == 422
    analysis = await client.patch(
        f"/api/v1/projects/{project['id']}/issues/{issue['id']}",
        json={"status": "IN_ANALYSIS"},
        headers=headers,
    )
    assert analysis.status_code == 200
    resolved = await client.post(
        f"/api/v1/projects/{project['id']}/issues/{issue['id']}/resolve",
        json={"resolution": "Service restored", "actual_delay_days": 2, "actual_cost": "50"},
        headers=headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolved_at"] is not None
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/issues/{issue['id']}",
            json={"status": "OPEN"},
            headers=headers,
        )
    ).status_code == 409
    summary = (await client.get(f"/api/v1/projects/{project['id']}/control/summary")).json()
    assert summary["open_issues"] == 0
    assert summary["critical_issues"] == 0
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/issues/{issue['id']}/close", headers=headers
        )
    ).json()["status"] == "CLOSED"
    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert {"issue.created", "issue.status_changed", "issue.resolved", "issue.closed"} <= actions


async def test_change_approval_and_rejection_are_explicit_and_non_automatic(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "control-changes@example.com")
    project = await create_project(client, headers, "CTRL-CHANGE")
    task = (
        await client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"title": "Original task", "due_date": "2026-09-10"},
            headers=headers,
        )
    ).json()
    risk = await create_risk(client, headers, project["id"], "Linked risk")
    issue = await create_issue(client, headers, project["id"], "Linked issue")
    change = await create_change(
        client,
        headers,
        project["id"],
        "Extend delivery",
        reason="Dependency delay",
        schedule_impact="HIGH",
        estimated_delay_days=7,
        task_ids=[task["id"]],
        risk_ids=[risk["id"]],
        issue_ids=[issue["id"]],
    )
    assert change["status"] == "DRAFT"
    submitted = await client.post(
        f"/api/v1/projects/{project['id']}/changes/{change['id']}/submit", headers=headers
    )
    assert submitted.json()["status"] == "PENDING"
    assert (
        await client.post(
            f"/api/v1/projects/{project['id']}/changes/{change['id']}/approve",
            json={"decision": ""},
            headers=headers,
        )
    ).status_code == 422
    approved = await client.post(
        f"/api/v1/projects/{project['id']}/changes/{change['id']}/approve",
        json={"decision": "Approved by steering committee"},
        headers=headers,
    )
    assert approved.json()["status"] == "APPROVED"
    unchanged_task = (
        await client.get(f"/api/v1/projects/{project['id']}/tasks/{task['id']}")
    ).json()
    assert unchanged_task["due_date"] == "2026-09-10"
    implemented = await client.post(
        f"/api/v1/projects/{project['id']}/changes/{change['id']}/implement", headers=headers
    )
    assert implemented.json()["status"] == "IMPLEMENTED"
    assert (
        await client.patch(
            f"/api/v1/projects/{project['id']}/changes/{change['id']}",
            json={"title": "Locked"},
            headers=headers,
        )
    ).status_code == 409

    rejected_change = await create_change(client, headers, project["id"], "Rejected option")
    await client.post(
        f"/api/v1/projects/{project['id']}/changes/{rejected_change['id']}/submit",
        headers=headers,
    )
    rejected = await client.post(
        f"/api/v1/projects/{project['id']}/changes/{rejected_change['id']}/reject",
        json={"decision": "Benefits do not justify cost"},
        headers=headers,
    )
    assert rejected.json()["status"] == "REJECTED"
    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert {
        "change_request.created",
        "change_request.submitted",
        "change_request.approved",
        "change_request.implemented",
        "change_request.rejected",
    } <= actions


async def test_control_ownership_cross_project_and_owner_member_protection(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await login_as(client, session, "control-owner@example.com")
    first = await create_project(client, headers, "CTRL-OWNER-1")
    second = await create_project(client, headers, "CTRL-OWNER-2")
    foreign_member = await add_member(client, headers, second["id"], "Foreign Owner")
    assert (
        await client.post(
            f"/api/v1/projects/{first['id']}/risks",
            json={
                "title": "Wrong owner",
                "probability": 2,
                "impact": 2,
                "identified_date": "2026-08-29",
                "owner_member_id": foreign_member["id"],
            },
            headers=headers,
        )
    ).status_code == 422
    foreign_risk = await create_risk(client, headers, second["id"], "Foreign risk")
    assert (
        await client.post(
            f"/api/v1/projects/{first['id']}/changes",
            json={
                "title": "Wrong link",
                "requested_date": "2026-08-29",
                "risk_ids": [foreign_risk["id"]],
            },
            headers=headers,
        )
    ).status_code == 422
    other_headers = await login_as(client, session, "control-owner-other@example.com")
    assert (await client.get(f"/api/v1/projects/{first['id']}/risks")).status_code == 404
    assert (
        await client.post(
            f"/api/v1/projects/{second['id']}/issues",
            json={"title": "No access", "identified_date": "2026-08-29"},
            headers=other_headers,
        )
    ).status_code == 404
