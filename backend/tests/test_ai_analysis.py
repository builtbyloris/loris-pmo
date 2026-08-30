import json
from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context import ProjectContext
from app.ai.dependencies import get_ai_provider
from app.ai.errors import AIProviderTimeoutError
from app.ai.provider import AIRequest, AIResponse, AIUsage
from app.auth.passwords import hash_password
from app.models.ai import AIInsight, AIRecommendation
from app.models.audit import AuditEvent
from app.models.memory import ProjectLogEntry
from app.models.task import Task, TaskPriority, TaskStatus
from app.repositories.users import UserRepository
from app.schemas.ai import AIEvidenceRead, AIEvidenceType
from app.services.ai_analysis import AIAnalysisService

PASSWORD = "a secure analysis test password"


class AnalysisProvider:
    provider_name = "fake"
    model_name = "fake-analysis"
    available = True
    unavailable_reason = None

    def __init__(self, *, fabricated: bool = False, error: Exception | None = None) -> None:
        self.fabricated = fabricated
        self.error = error
        self.recommendation_title = "Review the affected work"
        self.requests: list[AIRequest] = []

    async def generate(self, request: AIRequest) -> AIResponse:
        self.requests.append(request)
        if self.error:
            raise self.error
        candidates = json.loads(request.user_message.split("\n")[-1])
        signal = candidates[0]
        evidence = ["task:fabricated"] if self.fabricated else signal["evidence_refs"]
        output = {
            "insights": [
                {
                    "signal_key": signal["signal_key"],
                    "type": signal["type"],
                    "severity": signal["severity"],
                    "title": "Delivery condition needs attention",
                    "summary": "A verified deterministic condition is active.",
                    "explanation": "The supplied alert indicates an unresolved condition.",
                    "evidence_refs": evidence,
                    "confidence": 0.91,
                }
            ],
            "recommendations": [
                {
                    "signal_key": signal["signal_key"],
                    "title": self.recommendation_title,
                    "recommendation": "Consider reviewing the affected work with its owner.",
                    "reasoning_summary": "The condition is active and supported by evidence.",
                    "expected_impact": "A clearer recovery decision.",
                    "alternatives": ["Accept the documented risk"],
                    "evidence_refs": evidence,
                    "confidence": 0.82,
                }
            ],
        }
        return AIResponse(
            text=json.dumps(output),
            provider=self.provider_name,
            model=self.model_name,
            usage=AIUsage(input_tokens=80, output_tokens=40, total_tokens=120),
        )


async def login(client: AsyncClient, session: AsyncSession, email: str):
    user = await UserRepository(session).create(email=email, password_hash=hash_password(PASSWORD))
    await session.commit()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return user, {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


async def project_with_overdue_task(
    client: AsyncClient, session: AsyncSession, headers: dict[str, str], code: str
) -> tuple[dict, UUID]:
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": f"Analysis {code}",
            "code": code,
            "target_end_date": (date.today() + timedelta(days=20)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 201
    project = response.json()
    task = Task(
        project_id=UUID(project["id"]),
        title="Overdue analysis task",
        status=TaskStatus.TODO,
        priority=TaskPriority.CRITICAL,
        due_date=date.today() - timedelta(days=4),
    )
    session.add(task)
    await session.commit()
    return project, task.id


def use_provider(client: AsyncClient, provider) -> None:
    client._transport.app.dependency_overrides[get_ai_provider] = lambda: provider  # type: ignore[attr-defined]


def test_candidate_builder_includes_health_decline_and_meeting_actions() -> None:
    context = ProjectContext(
        sections={
            "intelligence": {
                "active_alerts": [],
                "health": {
                    "history": [
                        {"id": "snapshot-new", "score": 62, "status": "AT_RISK"},
                        {"id": "snapshot-old", "score": 80, "status": "HEALTHY"},
                    ]
                },
            },
            "memory": {
                "pending_action_items": [
                    {
                        "evidence_ref": "meeting_action:one",
                        "description": "Confirm launch owner",
                        "status": "CONFIRMED",
                        "due_date": (date.today() - timedelta(days=1)).isoformat(),
                    }
                ]
            },
        },
        evidence={
            "health:overall": AIEvidenceRead(
                ref="health:overall",
                type=AIEvidenceType.HEALTH,
                label="Health",
                detail="Score 62",
            ),
            "meeting_action:one": AIEvidenceRead(
                ref="meeting_action:one",
                type=AIEvidenceType.MEETING_ACTION,
                label="Confirm launch owner",
                detail="CONFIRMED",
            ),
        },
        topics=("memory", "work"),
    )
    candidates = AIAnalysisService._candidates(context)
    assert [item["type"] for item in candidates] == [
        "health_decline",
        "unresolved_meeting_action",
    ]
    assert candidates[0]["severity"] == "CRITICAL"
    assert candidates[1]["facts"]["overdue"] is True


async def test_analysis_persists_deduplicates_and_records_lifecycle_without_task_mutation(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await login(client, session, "analysis@example.com")
    project, task_id = await project_with_overdue_task(client, session, headers, "AI-ANALYSIS")
    provider = AnalysisProvider()
    use_provider(client, provider)
    path = f"/api/v1/projects/{project['id']}/ai"

    first = await client.post(f"{path}/analyze", json={"language": "en"}, headers=headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["generated"] is True
    assert len(body["insights"]) == len(body["recommendations"]) == 1
    assert body["insights"][0]["evidence"][0]["type"] == "alert"
    assert body["recommendations"][0]["status"] == "PENDING"
    assert body["summary"]["usage"]["total_tokens"] == 120

    unchanged = await client.post(f"{path}/analyze", json={}, headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["unchanged"] is True
    assert len(provider.requests) == 1

    forced = await client.post(f"{path}/analyze", json={"force": True}, headers=headers)
    assert forced.status_code == 200
    assert len(provider.requests) == 2
    assert forced.json()["insights"][0]["id"] == body["insights"][0]["id"]
    assert forced.json()["recommendations"][0]["id"] == body["recommendations"][0]["id"]

    recommendation_id = body["recommendations"][0]["id"]
    accepted = await client.post(
        f"{path}/recommendations/{recommendation_id}/accept",
        json={"reason": "This is the best next step."},
        headers=headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"
    provider.recommendation_title = "A rewritten recommendation must not replace history"
    refreshed = await client.post(f"{path}/analyze", json={"force": True}, headers=headers)
    assert refreshed.status_code == 200
    stored = await client.get(f"{path}/recommendations/{recommendation_id}")
    assert stored.json()["title"] == "Review the affected work"
    repeat = await client.post(
        f"{path}/recommendations/{recommendation_id}/reject",
        json={},
        headers=headers,
    )
    assert repeat.status_code == 409
    task = await session.get(Task, task_id)
    assert task.status == TaskStatus.TODO
    assert task.due_date == date.today() - timedelta(days=4)
    assert (
        await session.scalar(
            select(func.count(ProjectLogEntry.id)).where(
                ProjectLogEntry.title.like("AI recommendation accepted:%")
            )
        )
        == 1
    )

    insight_id = body["insights"][0]["id"]
    dismissed = await client.post(f"{path}/insights/{insight_id}/dismiss", headers=headers)
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "DISMISSED"
    actions = set((await session.execute(select(AuditEvent.action))).scalars())
    assert {
        "ai.analysis_requested",
        "ai.analysis_succeeded",
        "ai.insight_generated",
        "ai.recommendation_generated",
        "ai.recommendation_accepted",
        "ai.insight_dismissed",
    } <= actions


async def test_fabricated_evidence_is_rejected_and_empty_project_skips_provider(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await login(client, session, "evidence@example.com")
    project, _ = await project_with_overdue_task(client, session, headers, "AI-EVIDENCE")
    provider = AnalysisProvider(fabricated=True)
    use_provider(client, provider)
    response = await client.post(
        f"/api/v1/projects/{project['id']}/ai/analyze", json={}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["insights"] == []
    assert response.json()["recommendations"] == []
    assert await session.scalar(select(func.count(AIInsight.id))) == 0
    assert await session.scalar(select(func.count(AIRecommendation.id))) == 0

    empty = await client.post(
        "/api/v1/projects",
        json={"name": "Empty", "code": "AI-EMPTY"},
        headers=headers,
    )
    assert empty.status_code == 201
    no_signals = await client.post(
        f"/api/v1/projects/{empty.json()['id']}/ai/analyze", json={}, headers=headers
    )
    assert no_signals.status_code == 200
    assert no_signals.json()["generated"] is False
    assert len(provider.requests) == 1


async def test_analysis_failure_is_safe_and_owner_scoped(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await login(client, session, "failure@example.com")
    project, _ = await project_with_overdue_task(client, session, headers, "AI-FAILURE")
    use_provider(client, AnalysisProvider(error=AIProviderTimeoutError("private")))
    response = await client.post(
        f"/api/v1/projects/{project['id']}/ai/analyze", json={}, headers=headers
    )
    assert response.status_code == 504
    assert "private" not in response.text
    assert await session.scalar(select(func.count(AIInsight.id))) == 0
    assert await session.scalar(select(func.count(AIRecommendation.id))) == 0

    _, other_headers = await login(client, session, "other-analysis@example.com")
    hidden = await client.get(
        f"/api/v1/projects/{project['id']}/ai/insights", headers=other_headers
    )
    assert hidden.status_code == 404


@pytest.mark.parametrize(("action", "status"), [("reject", "REJECTED"), ("ignore", "IGNORED")])
async def test_recommendation_reject_and_ignore_lifecycle(
    client: AsyncClient,
    session: AsyncSession,
    action: str,
    status: str,
) -> None:
    _, headers = await login(client, session, f"{action}@example.com")
    project, _ = await project_with_overdue_task(client, session, headers, f"AI-{action.upper()}")
    use_provider(client, AnalysisProvider())
    path = f"/api/v1/projects/{project['id']}/ai"
    analyzed = await client.post(f"{path}/analyze", json={}, headers=headers)
    recommendation_id = analyzed.json()["recommendations"][0]["id"]
    reviewed = await client.post(
        f"{path}/recommendations/{recommendation_id}/{action}",
        json={"reason": "Recorded human decision"},
        headers=headers,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == status
    assert reviewed.json()["decision_reason"] == "Recorded human decision"


async def test_cleared_signal_resolves_insight_and_expires_pending_recommendation(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await login(client, session, "resolution@example.com")
    project, task_id = await project_with_overdue_task(client, session, headers, "AI-RESOLUTION")
    provider = AnalysisProvider()
    use_provider(client, provider)
    path = f"/api/v1/projects/{project['id']}/ai"
    first = await client.post(f"{path}/analyze", json={}, headers=headers)
    assert first.status_code == 200
    task = await session.get(Task, task_id)
    task.status = TaskStatus.DONE
    task.completion_percentage = 100
    await session.commit()

    cleared = await client.post(f"{path}/analyze", json={}, headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["insights"][0]["status"] == "RESOLVED"
    assert cleared.json()["recommendations"][0]["status"] == "EXPIRED"
    assert len(provider.requests) == 1


async def test_ai_analysis_endpoints_require_auth(client: AsyncClient) -> None:
    project_id = uuid4()
    assert (await client.get(f"/api/v1/projects/{project_id}/ai/analysis")).status_code == 401
    assert (
        await client.post(f"/api/v1/projects/{project_id}/ai/analyze", json={})
    ).status_code == 401
