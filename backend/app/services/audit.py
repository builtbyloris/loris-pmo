from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent


class AuditService:
    def __init__(self, session: AsyncSession, actor_user_id: UUID) -> None:
        self.session = session
        self.actor_user_id = actor_user_id

    def record(
        self,
        *,
        project_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: UUID,
        changes: dict | None = None,
    ) -> None:
        self.session.add(
            AuditEvent(
                actor_user_id=self.actor_user_id,
                project_id=project_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes,
            )
        )
