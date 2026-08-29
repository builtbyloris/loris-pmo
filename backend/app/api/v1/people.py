from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.schemas.people import (
    MemberCreate,
    MemberRead,
    MemberUpdate,
    MemberWorkload,
    PeopleSummary,
    PersonCreate,
    PersonRead,
    PersonUpdate,
    StakeholderCreate,
    StakeholderRead,
    StakeholderUpdate,
)
from app.services.people import PeopleService

people_router = APIRouter(prefix="/people", tags=["people"])
project_router = APIRouter(prefix="/projects/{project_id}", tags=["people"])
Session = Annotated[AsyncSession, Depends(get_db)]


@people_router.get("", response_model=list[PersonRead])
async def list_people(
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> list[PersonRead]:
    return [
        PersonRead.model_validate(item)
        for item in await PeopleService(session, user.id).list_people(search)
    ]


@people_router.post(
    "",
    response_model=PersonRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_person(data: PersonCreate, user: CurrentUser, session: Session) -> PersonRead:
    return PersonRead.model_validate(await PeopleService(session, user.id).create_person(data))


@people_router.patch(
    "/{person_id}", response_model=PersonRead, dependencies=[Depends(require_csrf)]
)
async def update_person(
    person_id: UUID, data: PersonUpdate, user: CurrentUser, session: Session
) -> PersonRead:
    return PersonRead.model_validate(
        await PeopleService(session, user.id).update_person(person_id, data)
    )


@project_router.get("/members", response_model=list[MemberRead])
async def list_members(project_id: UUID, user: CurrentUser, session: Session) -> list[MemberRead]:
    return [
        MemberRead.model_validate(item)
        for item in await PeopleService(session, user.id).list_members(project_id)
    ]


@project_router.post(
    "/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def add_member(
    project_id: UUID, data: MemberCreate, user: CurrentUser, session: Session
) -> MemberRead:
    return MemberRead.model_validate(
        await PeopleService(session, user.id).add_member(project_id, data)
    )


@project_router.patch(
    "/members/{member_id}", response_model=MemberRead, dependencies=[Depends(require_csrf)]
)
async def update_member(
    project_id: UUID,
    member_id: UUID,
    data: MemberUpdate,
    user: CurrentUser,
    session: Session,
) -> MemberRead:
    return MemberRead.model_validate(
        await PeopleService(session, user.id).update_member(project_id, member_id, data)
    )


@project_router.delete(
    "/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def remove_member(
    project_id: UUID, member_id: UUID, user: CurrentUser, session: Session
) -> None:
    await PeopleService(session, user.id).remove_member(project_id, member_id)


@project_router.get("/stakeholders", response_model=list[StakeholderRead])
async def list_stakeholders(
    project_id: UUID, user: CurrentUser, session: Session
) -> list[StakeholderRead]:
    return await PeopleService(session, user.id).list_stakeholders(project_id)


@project_router.post(
    "/stakeholders",
    response_model=StakeholderRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_stakeholder(
    project_id: UUID, data: StakeholderCreate, user: CurrentUser, session: Session
) -> StakeholderRead:
    return await PeopleService(session, user.id).create_stakeholder(project_id, data)


@project_router.patch(
    "/stakeholders/{stakeholder_id}",
    response_model=StakeholderRead,
    dependencies=[Depends(require_csrf)],
)
async def update_stakeholder(
    project_id: UUID,
    stakeholder_id: UUID,
    data: StakeholderUpdate,
    user: CurrentUser,
    session: Session,
) -> StakeholderRead:
    return await PeopleService(session, user.id).update_stakeholder(
        project_id, stakeholder_id, data
    )


@project_router.delete(
    "/stakeholders/{stakeholder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def remove_stakeholder(
    project_id: UUID,
    stakeholder_id: UUID,
    user: CurrentUser,
    session: Session,
) -> None:
    await PeopleService(session, user.id).remove_stakeholder(project_id, stakeholder_id)


@project_router.get("/workload", response_model=list[MemberWorkload])
async def project_workload(
    project_id: UUID, user: CurrentUser, session: Session
) -> list[MemberWorkload]:
    return await PeopleService(session, user.id).workload(project_id)


@project_router.get("/people/summary", response_model=PeopleSummary)
async def people_summary(project_id: UUID, user: CurrentUser, session: Session) -> PeopleSummary:
    return await PeopleService(session, user.id).summary(project_id)
