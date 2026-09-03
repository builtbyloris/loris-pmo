"""V2.1 collaboration endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.models.collaboration import CommentEntityType
from app.schemas.collaboration import (
    CollaboratorCreate,
    CollaboratorRead,
    CollaboratorUpdate,
    CommentCreate,
    CommentRead,
    CommentUpdate,
    NotificationList,
    NotificationRead,
    ProjectAccessRead,
)
from app.services.collaboration import CollaborationService, NotificationService

router = APIRouter(tags=["collaboration"])


@router.get("/projects/{project_id}/access", response_model=ProjectAccessRead)
async def access(
    project_id: UUID, user: CurrentUser, session: Annotated[AsyncSession, Depends(get_db)]
):
    return await CollaborationService(session, user.id).access(project_id)


@router.get("/projects/{project_id}/collaborators", response_model=list[CollaboratorRead])
async def collaborators(
    project_id: UUID, user: CurrentUser, session: Annotated[AsyncSession, Depends(get_db)]
):
    return await CollaborationService(session, user.id).list_collaborators(project_id)


@router.post(
    "/projects/{project_id}/collaborators",
    response_model=CollaboratorRead,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
async def add_collaborator(
    project_id: UUID,
    data: CollaboratorCreate,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return await CollaborationService(session, user.id).add_collaborator(project_id, data)


@router.patch(
    "/projects/{project_id}/collaborators/{membership_id}",
    response_model=CollaboratorRead,
    dependencies=[Depends(require_csrf)],
)
async def update_collaborator(
    project_id: UUID,
    membership_id: UUID,
    data: CollaboratorUpdate,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return await CollaborationService(session, user.id).update_collaborator(
        project_id, membership_id, data
    )


@router.delete(
    "/projects/{project_id}/collaborators/{membership_id}",
    status_code=204,
    dependencies=[Depends(require_csrf)],
)
async def remove_collaborator(
    project_id: UUID,
    membership_id: UUID,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    await CollaborationService(session, user.id).remove_collaborator(project_id, membership_id)


@router.get("/projects/{project_id}/comments", response_model=list[CommentRead])
async def comments(
    project_id: UUID,
    entity_type: CommentEntityType,
    entity_id: UUID,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return await CollaborationService(session, user.id).list_comments(
        project_id, entity_type, entity_id
    )


@router.post(
    "/projects/{project_id}/comments",
    response_model=CommentRead,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
async def add_comment(
    project_id: UUID,
    data: CommentCreate,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return await CollaborationService(session, user.id).create_comment(project_id, data)


@router.patch(
    "/projects/{project_id}/comments/{comment_id}",
    response_model=CommentRead,
    dependencies=[Depends(require_csrf)],
)
async def update_comment(
    project_id: UUID,
    comment_id: UUID,
    data: CommentUpdate,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return await CollaborationService(session, user.id).update_comment(project_id, comment_id, data)


@router.delete(
    "/projects/{project_id}/comments/{comment_id}",
    status_code=204,
    dependencies=[Depends(require_csrf)],
)
async def delete_comment(
    project_id: UUID,
    comment_id: UUID,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    await CollaborationService(session, user.id).delete_comment(project_id, comment_id)


@router.get("/notifications", response_model=NotificationList)
async def notifications(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    return await NotificationService(session, user.id).list(limit)


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationRead,
    dependencies=[Depends(require_csrf)],
)
async def mark_notification_read(
    notification_id: UUID, user: CurrentUser, session: Annotated[AsyncSession, Depends(get_db)]
):
    return await NotificationService(session, user.id).mark_read(notification_id)


@router.post("/notifications/read-all", status_code=204, dependencies=[Depends(require_csrf)])
async def mark_all_notifications_read(
    user: CurrentUser, session: Annotated[AsyncSession, Depends(get_db)]
):
    await NotificationService(session, user.id).mark_all_read()
