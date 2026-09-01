import math

import httpx

from app.ai.embeddings import EmbeddingPurpose, EmbeddingResponse
from app.ai.errors import (
    AIInvalidResponseError,
    AIProviderAuthenticationError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)


class GeminiEmbeddingProvider:
    """Server-only Gemini embedding adapter; request text is never logged."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        dimensions: int,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._dimensions = dimensions
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def available(self) -> bool:
        return True

    @property
    def unavailable_reason(self) -> None:
        return None

    async def embed(
        self, texts: tuple[str, ...], *, purpose: EmbeddingPurpose
    ) -> EmbeddingResponse:
        if not texts:
            return EmbeddingResponse(vectors=(), provider=self.provider_name, model=self.model_name)
        instruction = (
            "task: retrieval document | content: "
            if purpose == EmbeddingPurpose.DOCUMENT
            else "task: retrieval query | query: "
        )
        model_resource = f"models/{self._model}"
        payload = {
            "requests": [
                {
                    "model": model_resource,
                    "content": {"parts": [{"text": f"{instruction}{text}"}]},
                    "output_dimensionality": self._dimensions,
                }
                for text in texts
            ]
        }
        endpoint = f"{self._base_url}/models/{self._model}:batchEmbedContents"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    headers={"x-goog-api-key": self._api_key},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise AIProviderTimeoutError("Gemini embedding request timed out.") from exc
        except httpx.RequestError as exc:
            raise AIProviderUnavailableError("Gemini embeddings could not be reached.") from exc
        if response.status_code in (401, 403):
            raise AIProviderAuthenticationError("Gemini rejected the configured credentials.")
        if response.status_code == 429:
            raise AIProviderRateLimitError("Gemini embedding rate limit reached.")
        if response.status_code >= 400:
            raise AIProviderUnavailableError("Gemini returned an unsuccessful embedding response.")
        try:
            body = response.json()
            embeddings = body["embeddings"]
            if not isinstance(embeddings, list) or len(embeddings) != len(texts):
                raise TypeError
            vectors = tuple(_vector(item, self._dimensions) for item in embeddings)
            usage = body.get("usageMetadata") or {}
            tokens = usage.get("promptTokenCount")
        except (KeyError, TypeError, ValueError) as exc:
            raise AIInvalidResponseError("Gemini returned malformed embeddings.") from exc
        return EmbeddingResponse(
            vectors=vectors,
            provider=self.provider_name,
            model=self.model_name,
            input_tokens=tokens if isinstance(tokens, int) and tokens >= 0 else None,
        )


def _vector(item: object, dimensions: int) -> tuple[float, ...]:
    if not isinstance(item, dict) or not isinstance(item.get("values"), list):
        raise TypeError
    vector = tuple(float(value) for value in item["values"])
    if len(vector) != dimensions or not all(math.isfinite(value) for value in vector):
        raise ValueError
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude <= 0:
        raise ValueError
    return tuple(value / magnitude for value in vector)
