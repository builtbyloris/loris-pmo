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
    """Isolated Gemini Interactions adapter with one schema-constrained request."""

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
        # Retained for constructor/configuration compatibility. The Interactions API
        # does not currently expose temperature in its generation configuration.
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
        interaction_input = [
            {
                "type": "model_output" if role == "assistant" else "user_input",
                "content": [{"type": "text", "text": text}],
            }
            for role, text in request.history
        ]
        interaction_input.append(
            {
                "type": "user_input",
                "content": [{"type": "text", "text": request.user_message}],
            }
        )
        provider_input: str | list[dict[str, object]] = (
            interaction_input if request.history else request.user_message
        )
        payload = {
            "model": self._model,
            "input": provider_input,
            "system_instruction": request.system_instruction,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": _interaction_schema(request.response_schema),
            },
            "generation_config": {"max_output_tokens": self._max_output_tokens},
            "store": False,
        }
        endpoint = f"{self._base_url}/interactions"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "x-goog-api-key": self._api_key,
                        "Api-Revision": "2026-05-20",
                    },
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
            if not isinstance(body, dict):
                raise TypeError
            status = body.get("status")
            if status != "completed":
                if status in {"failed", "cancelled"}:
                    raise AIProviderUnavailableError("Gemini did not complete the interaction.")
                raise AIInvalidResponseError("Gemini returned an incomplete interaction.")
            steps = body["steps"]
            if not isinstance(steps, list):
                raise TypeError
            text = "".join(
                content.get("text", "")
                for step in steps
                if isinstance(step, dict)
                and step.get("type") == "model_output"
                and step.get("status") in (None, "done")
                for content in step.get("content", [])
                if isinstance(content, dict) and content.get("type") == "text"
            ).strip()
        except AIInvalidResponseError:
            raise
        except AIProviderUnavailableError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise AIInvalidResponseError("Gemini returned a malformed response.") from exc
        if not text:
            raise AIInvalidResponseError("Gemini returned an empty response.")

        usage = body.get("usage") or {}
        if not isinstance(usage, dict):
            usage = {}
        response_model = body.get("model")
        return AIResponse(
            text=text,
            provider=self.provider_name,
            model=(
                response_model
                if isinstance(response_model, str) and response_model.strip()
                else self.model_name
            ),
            usage=AIUsage(
                input_tokens=_optional_nonnegative_int(usage.get("total_input_tokens")),
                output_tokens=_optional_nonnegative_int(usage.get("total_output_tokens")),
                total_tokens=_optional_nonnegative_int(usage.get("total_tokens")),
            ),
        )


def _interaction_schema(value: object) -> object:
    """Translate JSON Schema to the subset accepted by Gemini structured output."""
    if isinstance(value, dict):
        return {
            key: _interaction_schema(item)
            for key, item in value.items()
            if key not in {"minLength", "maxLength"}
        }
    if isinstance(value, list):
        return [_interaction_schema(item) for item in value]
    return value


def _optional_nonnegative_int(value: object) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None
