"""Central project authorization policy for V2 collaboration."""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.collaboration import MembershipStatus, ProjectAccessRole, ProjectMembership


class Capability(StrEnum):
    PROJECT_READ = "project.read"
    PROJECT_UPDATE = "project.update"
    PROJECT_ARCHIVE = "project.archive"
    MEMBERS_READ = "members.read"
    MEMBERS_MANAGE = "members.manage"
    MEMBERS_CHANGE_ROLE = "members.change_role"
    PEOPLE_READ = "people.read"
    PEOPLE_MANAGE = "people.manage"
    TASKS_READ = "tasks.read"
    TASKS_CREATE = "tasks.create"
    TASKS_UPDATE = "tasks.update"
    TASKS_DELETE = "tasks.delete"
    SCHEDULE_READ = "schedule.read"
    SCHEDULE_MANAGE = "schedule.manage"
    FINANCE_READ = "finance.read"
    FINANCE_MANAGE = "finance.manage"
    CONTROL_READ = "control.read"
    CONTROL_MANAGE = "control.manage"
    MEETINGS_READ = "meetings.read"
    MEETINGS_MANAGE = "meetings.manage"
    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_MANAGE = "documents.manage"
    REPORTS_READ = "reports.read"
    REPORTS_GENERATE = "reports.generate"
    AI_READ = "ai.read"
    AI_ASSISTANT = "ai.assistant"
    AI_GENERATE = "ai.generate"
    AI_CONFIRM_PROPOSALS = "ai.confirm_proposals"
    COMMENTS_READ = "comments.read"
    COMMENTS_WRITE = "comments.write"
    AUDIT_READ = "audit.read"


READ_CAPABILITIES = {
    Capability.PROJECT_READ,
    Capability.MEMBERS_READ,
    Capability.PEOPLE_READ,
    Capability.TASKS_READ,
    Capability.SCHEDULE_READ,
    Capability.CONTROL_READ,
    Capability.MEETINGS_READ,
    Capability.DOCUMENTS_READ,
    Capability.REPORTS_READ,
    Capability.AI_READ,
    Capability.COMMENTS_READ,
}
MANAGER_CAPABILITIES = READ_CAPABILITIES | {
    Capability.PROJECT_UPDATE,
    Capability.PEOPLE_MANAGE,
    Capability.TASKS_CREATE,
    Capability.TASKS_UPDATE,
    Capability.TASKS_DELETE,
    Capability.SCHEDULE_MANAGE,
    Capability.FINANCE_READ,
    Capability.FINANCE_MANAGE,
    Capability.CONTROL_MANAGE,
    Capability.MEETINGS_MANAGE,
    Capability.DOCUMENTS_MANAGE,
    Capability.REPORTS_GENERATE,
    Capability.AI_ASSISTANT,
    Capability.AI_GENERATE,
    Capability.AI_CONFIRM_PROPOSALS,
    Capability.COMMENTS_WRITE,
    Capability.AUDIT_READ,
}
ROLE_CAPABILITIES: dict[ProjectAccessRole, frozenset[Capability]] = {
    ProjectAccessRole.OWNER: frozenset(
        MANAGER_CAPABILITIES
        | {Capability.PROJECT_ARCHIVE, Capability.MEMBERS_MANAGE, Capability.MEMBERS_CHANGE_ROLE}
    ),
    ProjectAccessRole.PROJECT_ADMIN: frozenset(
        MANAGER_CAPABILITIES | {Capability.MEMBERS_MANAGE, Capability.MEMBERS_CHANGE_ROLE}
    ),
    ProjectAccessRole.PROJECT_MANAGER: frozenset(MANAGER_CAPABILITIES),
    ProjectAccessRole.CONTRIBUTOR: frozenset(
        READ_CAPABILITIES
        | {
            Capability.TASKS_CREATE,
            Capability.TASKS_UPDATE,
            Capability.MEETINGS_MANAGE,
            Capability.AI_ASSISTANT,
            Capability.COMMENTS_WRITE,
        }
    ),
    ProjectAccessRole.VIEWER: frozenset(READ_CAPABILITIES),
}


def accessible_project_ids(user_id: UUID) -> Select[tuple[UUID]]:
    return select(ProjectMembership.project_id).where(
        ProjectMembership.user_id == user_id,
        ProjectMembership.status == MembershipStatus.ACTIVE,
    )


class AuthorizationService:
    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    async def membership(self, project_id: UUID) -> ProjectMembership:
        result = await self.session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == self.user_id,
                ProjectMembership.status == MembershipStatus.ACTIVE,
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        return membership

    async def require(self, project_id: UUID, capability: Capability) -> ProjectMembership:
        membership = await self.membership(project_id)
        if capability not in ROLE_CAPABILITIES[membership.role]:
            raise AppError(
                code="insufficient_project_permission",
                message="Your project role does not allow this action.",
                status_code=403,
            )
        return membership

    async def can(self, project_id: UUID, capability: Capability) -> bool:
        try:
            membership = await self.membership(project_id)
        except AppError:
            return False
        return capability in ROLE_CAPABILITIES[membership.role]

    @staticmethod
    def capabilities(role: ProjectAccessRole) -> list[str]:
        return sorted(capability.value for capability in ROLE_CAPABILITIES[role])
