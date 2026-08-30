from urllib.parse import quote

import httpx

from app.ai.errors import (
    AIInvalidResponseError,
    AIProviderAuthenticationError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.ai.provider import AIRequest, AIResponse, AIUsage


class GeminiProvider:
    """Isolated Gemini REST adapter with one bounded, schema-constrained request."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        temperature: float,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._temperature = temperature
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

    async def generate(self, request: AIRequest) -> AIResponse:
        contents = [
            {"role": "model" if role == "assistant" else "user", "parts": [{"text": text}]}
            for role, text in request.history
        ]
        contents.append({"role": "user", "parts": [{"text": request.user_message}]})
        payload = {
            "systemInstruction": {"parts": [{"text": request.system_instruction}]},
            "contents": contents,
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_output_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": request.response_schema,
            },
        }
        endpoint = f"{self._base_url}/models/{quote(self._model, safe='')}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    headers={"x-goog-api-key": self._api_key},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise AIProviderTimeoutError("Gemini request timed out.") from exc
        except httpx.RequestError as exc:
            raise AIProviderUnavailableError("Gemini could not be reached.") from exc

        if response.status_code in (401, 403):
            raise AIProviderAuthenticationError("Gemini rejected the configured credentials.")
        if response.status_code == 429:
            raise AIProviderRateLimitError("Gemini rate limit reached.")
        if response.status_code >= 400:
            raise AIProviderUnavailableError("Gemini returned an unsuccessful response.")

        try:
            body = response.json()
            candidates = body["candidates"]
            parts = candidates[0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIInvalidResponseError("Gemini returned a malformed response.") from exc
        if not text:
            raise AIInvalidResponseError("Gemini returned an empty response.")

        usage = body.get("usageMetadata") or {}
        return AIResponse(
            text=text,
            provider=self.provider_name,
            model=self.model_name,
            usage=AIUsage(
                input_tokens=_optional_nonnegative_int(usage.get("promptTokenCount")),
                output_tokens=_optional_nonnegative_int(usage.get("candidatesTokenCount")),
                total_tokens=_optional_nonnegative_int(usage.get("totalTokenCount")),
            ),
        )


def _optional_nonnegative_int(value: object) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None
