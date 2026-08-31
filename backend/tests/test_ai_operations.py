import json
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.dependencies import get_ai_provider
from app.ai.provider import AIRequest, AIResponse, AIUsage
from app.auth.passwords import hash_password
from app.models.ai_operations import AIBriefing, AIScenario, MeetingAIProposal
from app.models.memory import (
    ActionItemStatus,
    Meeting,
    MeetingActionItem,
    MeetingParticipant,
    MeetingStatus,
)
from app.models.milestone import Milestone
from app.models.people import Person, ProjectMember
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.task_dependency import DependencyType, TaskDependency
from app.repositories.users import UserRepository

PASSWORD = "a secure operational ai test password"


class OperationsProvider:
    provider_name = "fake"
    model_name = "fake-operations"
    available = True
    unavailable_reason = None

    def __init__(self, fabricated_meeting_ref: bool = False):
        self.requests: list[AIRequest] = []
        self.fabricated_meeting_ref = fabricated_meeting_ref

    async def generate(self, request: AIRequest) -> AIResponse:
        self.requests.append(request)
        payload = json.loads(request.user_message.split("\n")[-1])
        properties = request.response_schema["properties"]
        if "attention_items" in properties:
            signal = payload["candidate_signals"][0]
            result = {
                "summary": "One item needs attention.",
                "attention_items": [
                    {
                        "priority": "critical",
                        "title": "Review delivery",
                        "reason": "A verified signal is active.",
                        "evidence_refs": signal["evidence_refs"],
                    }
                ],
                "suggested_focus": ["Review ownership"],
            }
        elif "executive_summary" in properties:
            refs = [value["evidence_ref"] for value in payload["facts"]["categories"].values()]
            result = {
                "executive_summary": "Audited activity summarized.",
                "progress": [],
                "setbacks": [],
                "decisions": [],
                "risks_and_issues": [],
                "financial_summary": "No material movement.",
                "next_week_focus": [],
                "evidence_refs": refs,
                "insufficient_history": False,
            }
        elif "interpretation" in properties:
            refs = [value["ref"] for value in payload["evidence_catalog"]]
            result = {
                "interpretation": "Simulation only.",
                "impacts": ["Schedule may move."],
                "options": ["Review sequencing."],
                "assumptions": [],
                "evidence_refs": refs,
            }
        else:
            meeting_ref = payload["required_meeting_evidence_ref"]
            evidence = ["meeting:fabricated"] if self.fabricated_meeting_ref else [meeting_ref]
            participant = payload["meeting"]["participant_member_ids"][0]
            result = {
                "summary": "The meeting identified an action.",
                "evidence_refs": evidence,
                "proposals": [
                    {
                        "proposal_key": "follow-up",
                        "kind": "ACTION_ITEM",
                        "title": "Confirm launch",
                        "description": "Confirm the launch owner.",
                        "owner_member_id": participant,
                        "due_date": (date.today() + timedelta(days=3)).isoformat(),
                        "evidence_refs": evidence,
                    }
                ],
            }
        return AIResponse(
            text=json.dumps(result),
            provider=self.provider_name,
            model=self.model_name,
            usage=AIUsage(input_tokens=50, output_tokens=25, total_tokens=75),
        )


async def login(client: AsyncClient, session: AsyncSession, email: str):
    user = await UserRepository(session).create(email=email, password_hash=hash_password(PASSWORD))
    await session.commit()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return user, {"X-CSRF-Token": client.cookies.get("loris_csrf_token")}


async def project(client, headers, code):
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": code,
            "code": code,
            "target_end_date": (date.today() + timedelta(days=30)).isoformat(),
            "planned_budget": "10000",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def use_provider(client, provider):
    client._transport.app.dependency_overrides[get_ai_provider] = lambda: provider  # type: ignore[attr-defined]


async def test_daily_briefing_is_evidence_backed_and_reused(
    client: AsyncClient, session: AsyncSession
):
    _, headers = await login(client, session, "daily@example.com")
    value = await project(client, headers, "DAILY-AI")
    task = Task(
        project_id=UUID(value["id"]),
        title="Late task",
        status=TaskStatus.TODO,
        priority=TaskPriority.CRITICAL,
        due_date=date.today() - timedelta(days=2),
    )
    session.add(task)
    await session.commit()
    provider = OperationsProvider()
    use_provider(client, provider)
    path = f"/api/v1/projects/{value['id']}/ai/daily-briefing/generate"
    first = await client.post(path, json={}, headers=headers)
    assert first.status_code == 200, first.text
    assert len(first.json()["content"]["attention_items"]) == 1
    assert first.json()["evidence"][0]["type"] == "alert"
    second = await client.post(path, json={}, headers=headers)
    assert second.status_code == 200 and second.json()["reused"] is True
    assert len(provider.requests) == 1
    assert await session.scalar(select(func.count(AIBriefing.id))) == 1


async def test_weekly_review_uses_rolling_audited_period(
    client: AsyncClient, session: AsyncSession
):
    _, headers = await login(client, session, "weekly@example.com")
    value = await project(client, headers, "WEEKLY-AI")
    provider = OperationsProvider()
    use_provider(client, provider)
    response = await client.post(
        f"/api/v1/projects/{value['id']}/ai/weekly-reviews/generate", json={}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["period_start"] and body["period_end"]
    assert body["content"]["insufficient_history"] is True
    assert all(item["type"] == "period_fact" for item in body["evidence"])


async def test_scenario_is_persisted_simulation_without_task_mutation(
    client: AsyncClient, session: AsyncSession
):
    _, headers = await login(client, session, "scenario@example.com")
    value = await project(client, headers, "SCENARIO-AI")
    project_id = UUID(value["id"])
    milestone = Milestone(
        project_id=project_id,
        title="Release",
        due_date=date.today() + timedelta(days=9),
    )
    session.add(milestone)
    await session.flush()
    tasks = [
        Task(
            project_id=project_id,
            milestone_id=milestone.id,
            title=title,
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            start_date=date.today() + timedelta(days=start),
            due_date=date.today() + timedelta(days=finish),
        )
        for title, start, finish in (("Design", 1, 3), ("Build", 4, 6), ("Delivery", 7, 9))
    ]
    session.add_all(tasks)
    await session.flush()
    session.add_all(
        TaskDependency(
            project_id=project_id,
            source_task_id=source.id,
            target_task_id=target.id,
            dependency_type=DependencyType.BLOCKS,
        )
        for source, target in zip(tasks, tasks[1:], strict=False)
    )
    await session.commit()
    original_dates = [(task.start_date, task.due_date) for task in tasks]
    provider = OperationsProvider()
    use_provider(client, provider)
    response = await client.post(
        f"/api/v1/projects/{value['id']}/ai/scenarios",
        json={"type": "TASK_DELAY", "task_id": str(tasks[0].id), "delay_days": 7},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    impact = response.json()["deterministic_impact"]
    assert impact["simulation_only"] is True
    assert len(impact["affected_tasks"]) == 3
    assert (
        impact["affected_tasks"][-1]["projected_finish"]
        == (date.today() + timedelta(days=16)).isoformat()
    )
    milestone_response = await client.post(
        f"/api/v1/projects/{value['id']}/ai/scenarios",
        json={
            "type": "MILESTONE_DELAY",
            "milestone_id": str(milestone.id),
            "delay_days": 4,
        },
        headers=headers,
    )
    assert milestone_response.status_code == 200, milestone_response.text
    assert (
        milestone_response.json()["deterministic_impact"]["milestone_impacts"][0]["projected_date"]
        == (milestone.due_date + timedelta(days=4)).isoformat()
    )
    for task, expected in zip(tasks, original_dates, strict=True):
        await session.refresh(task)
        assert (task.start_date, task.due_date) == expected
    await session.refresh(milestone)
    assert milestone.due_date == date.today() + timedelta(days=9)
    assert await session.scalar(select(func.count(AIScenario.id))) == 2


async def test_meeting_proposal_requires_confirmation_and_rejects_fabricated_evidence(
    client: AsyncClient, session: AsyncSession
):
    user, headers = await login(client, session, "meeting-ai@example.com")
    value = await project(client, headers, "MEETING-AI")
    person = Person(owner_user_id=user.id, name="Ada")
    session.add(person)
    await session.flush()
    member = ProjectMember(project_id=UUID(value["id"]), person_id=person.id)
    session.add(member)
    await session.flush()
    meeting = Meeting(
        project_id=UUID(value["id"]),
        title="Launch review",
        scheduled_at=datetime.now(UTC),
        notes="Ada will confirm the launch owner.",
        status=MeetingStatus.COMPLETED,
    )
    session.add(meeting)
    await session.flush()
    session.add(
        MeetingParticipant(
            project_id=UUID(value["id"]), meeting_id=meeting.id, project_member_id=member.id
        )
    )
    await session.commit()
    provider = OperationsProvider()
    use_provider(client, provider)
    base = f"/api/v1/projects/{value['id']}/ai/meetings/{meeting.id}"
    analyzed = await client.post(f"{base}/analyze", json={}, headers=headers)
    assert analyzed.status_code == 200, analyzed.text
    proposal = analyzed.json()["proposals"][0]
    assert proposal["status"] == "PENDING"
    assert await session.scalar(select(func.count(MeetingActionItem.id))) == 0
    confirmed = await client.post(f"{base}/proposals/{proposal['id']}/confirm", headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["proposal"]["status"] == "CONFIRMED"
    action = (await session.execute(select(MeetingActionItem))).scalar_one()
    assert action.status == ActionItemStatus.CONFIRMED
    repeat = await client.post(f"{base}/proposals/{proposal['id']}/confirm", headers=headers)
    assert repeat.status_code == 409

    other = await project(client, headers, "MEETING-BAD")
    bad_meeting = Meeting(
        project_id=UUID(other["id"]),
        title="Bad evidence",
        scheduled_at=datetime.now(UTC),
        notes="Propose an action.",
        status=MeetingStatus.COMPLETED,
    )
    session.add(bad_meeting)
    await session.flush()
    other_member = ProjectMember(project_id=UUID(other["id"]), person_id=person.id)
    session.add(other_member)
    await session.flush()
    session.add(
        MeetingParticipant(
            project_id=UUID(other["id"]),
            meeting_id=bad_meeting.id,
            project_member_id=other_member.id,
        )
    )
    await session.commit()
    use_provider(client, OperationsProvider(fabricated_meeting_ref=True))
    invalid = await client.post(
        f"/api/v1/projects/{other['id']}/ai/meetings/{bad_meeting.id}/analyze",
        json={},
        headers=headers,
    )
    assert invalid.status_code == 502
    assert (
        await session.scalar(
            select(func.count(MeetingAIProposal.id)).where(
                MeetingAIProposal.project_id == UUID(other["id"])
            )
        )
        == 0
    )
