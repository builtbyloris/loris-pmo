from app.ai.provider import AIRequest, AIResponse


class GeminiProvider:
    """Gemini adapter boundary; transport is added with the first approved AI use case."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, request: AIRequest) -> AIResponse:
        del request
        raise RuntimeError("Gemini execution is not enabled in the foundation release.")
