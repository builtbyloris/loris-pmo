from typing import Annotated

from fastapi import Depends

from app.ai.embeddings import EmbeddingProvider, UnavailableEmbeddingProvider
from app.ai.gemini import GeminiProvider
from app.ai.gemini_embeddings import GeminiEmbeddingProvider
from app.ai.provider import AIProvider, UnavailableAIProvider
from app.core.config import Settings, get_settings


def get_ai_provider(settings: Annotated[Settings, Depends(get_settings)]) -> AIProvider:
    if not settings.gemini_api_key:
        return UnavailableAIProvider(
            provider=settings.ai_provider,
            model=settings.gemini_model,
            reason="not_configured",
        )
    return GeminiProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout_seconds=settings.ai_timeout_seconds,
        max_output_tokens=settings.ai_max_output_tokens,
        temperature=settings.ai_temperature,
    )


def get_embedding_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingProvider:
    if not settings.gemini_api_key:
        return UnavailableEmbeddingProvider(
            provider=settings.ai_provider,
            model=settings.gemini_embedding_model,
            reason="not_configured",
        )
    return GeminiEmbeddingProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_embedding_model,
        timeout_seconds=settings.ai_timeout_seconds,
        dimensions=settings.embedding_dimensions,
    )
