from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context import ProjectContextBuilder
from app.ai.errors import (
    AIError,
    AIInvalidResponseError,
    AINotConfiguredError,
    AIProviderAuthenticationError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from app.ai.provider import AIProvider
from app.ai.service import AIService
from app.core.errors import AppError
from app.schemas.ai import AIChatRequest, AIChatResponse, AIStatusRead
from app.services.audit import AuditService
from app.services.projects import ProjectService


class ProjectAssistantService:
    def __init__(
        self,
        session: AsyncSession,
        owner_user_id: UUID,
        provider: AIProvider,
        *,
        context_builder: ProjectContextBuilder | None = None,
    ) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.ai = AIService(provider)
        self.context_builder = context_builder or ProjectContextBuilder(session, owner_user_id)
        self.audit = AuditService(session, owner_user_id)

    async def status(self, project_id: UUID) -> AIStatusRead:
        await ProjectService(self.session, self.owner_user_id).get(project_id)
        provider = self.ai.provider
        return AIStatusRead(
            available=provider.available,
            provider=provider.provider_name,
            model=provider.model_name,
            reason=provider.unavailable_reason,
        )

    async def chat(self, project_id: UUID, data: AIChatRequest) -> AIChatResponse:
        await ProjectService(self.session, self.owner_user_id).get(project_id)
        provider = self.ai.provider
        started = perf_counter()
        if not provider.available:
            await self._record(
                project_id,
                success=False,
                latency_ms=0,
                request_types=[],
                error_code="ai_not_configured",
            )
            raise AppError(
                code="ai_not_configured",
                message="AI assistance is not configured. Your project data is unaffected.",
                status_code=503,
            )

        try:
            context = await self.context_builder.build(project_id, data.message)
        except AppError:
            raise
        except Exception as exc:
            await self._record(
                project_id,
                success=False,
                latency_ms=self._latency(started),
                request_types=[],
                error_code="ai_context_unavailable",
            )
            raise AppError(
                code="ai_context_unavailable",
                message="AI context could not be prepared. Your project data is unaffected.",
                status_code=503,
            ) from exc

        try:
            result = await self.ai.chat(data, context)
        except AIError as exc:
            await self._record(
                project_id,
                success=False,
                latency_ms=self._latency(started),
                request_types=list(context.topics),
                error_code=exc.code,
            )
            raise self._public_error(exc) from exc

        await self._record(
            project_id,
            success=True,
            latency_ms=self._latency(started),
            request_types=list(context.topics),
            context_sections=result.context_sections,
            usage=result.usage.model_dump(),
        )
        return result

    async def _record(
        self,
        project_id: UUID,
        *,
        success: bool,
        latency_ms: int,
        request_types: list[str],
        context_sections: list[str] | None = None,
        usage: dict | None = None,
        error_code: str | None = None,
    ) -> None:
        provider = self.ai.provider
        self.audit.record(
            project_id=project_id,
            action="ai.chat_succeeded" if success else "ai.chat_failed",
            entity_type="ai_assistant",
            entity_id=project_id,
            changes={
                "provider": provider.provider_name,
                "model": provider.model_name,
                "success": success,
                "latency_ms": latency_ms,
                "request_types": request_types,
                "context_sections": context_sections or [],
                "usage": usage,
                "error_code": error_code,
            },
        )
        await self.session.commit()

    @staticmethod
    def _latency(started: float) -> int:
        return max(0, round((perf_counter() - started) * 1000))

    @staticmethod
    def _public_error(error: AIError) -> AppError:
        status = 504 if isinstance(error, AIProviderTimeoutError) else 503
        if isinstance(error, AIInvalidResponseError):
            status = 502
        message = "AI assistance is temporarily unavailable. Your project data is unaffected."
        if isinstance(error, AINotConfiguredError):
            message = "AI assistance is not configured. Your project data is unaffected."
        elif isinstance(error, AIProviderRateLimitError):
            message = (
                "AI assistance is busy. Please try again later. Your project data is unaffected."
            )
        elif isinstance(error, AIProviderAuthenticationError):
            message = "AI assistance is unavailable because its configuration was rejected."
        return AppError(code=error.code, message=message, status_code=status)
