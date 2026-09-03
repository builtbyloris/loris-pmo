"""FastAPI dependencies backed by the centralized authorization policy."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.models.collaboration import ProjectMembership
from app.services.authorization import AuthorizationService, Capability


def require_project_capability(
    capability: Capability,
) -> Callable[..., Coroutine[Any, Any, ProjectMembership]]:
    async def dependency(
        project_id: UUID,
        user: CurrentUser,
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> ProjectMembership:
        return await AuthorizationService(session, user.id).require(project_id, capability)

    return dependency


def authorize_project_module(
    read: Capability,
    write: Capability,
    *,
    create: Capability | None = None,
    delete: Capability | None = None,
    path_overrides: dict[str, Capability] | None = None,
) -> Callable[..., Coroutine[Any, Any, ProjectMembership]]:
    """Enforce one policy for every request handled by a project module router."""

    async def dependency(
        request: Request,
        project_id: UUID,
        user: CurrentUser,
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> ProjectMembership:
        capability = read if request.method == "GET" else write
        if request.method == "POST" and create is not None:
            capability = create
        elif request.method == "DELETE" and delete is not None:
            capability = delete
        for suffix, override in (path_overrides or {}).items():
            if request.url.path.endswith(suffix):
                capability = override
                break
        return await AuthorizationService(session, user.id).require(project_id, capability)

    return dependency
