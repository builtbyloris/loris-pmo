class AIError(Exception):
    code = "ai_unavailable"


class AINotConfiguredError(AIError):
    code = "ai_not_configured"


class AIProviderTimeoutError(AIError):
    code = "ai_timeout"


class AIProviderRateLimitError(AIError):
    code = "ai_rate_limited"


class AIProviderAuthenticationError(AIError):
    code = "ai_provider_authentication_failed"


class AIProviderUnavailableError(AIError):
    code = "ai_provider_unavailable"


class AIInvalidResponseError(AIError):
    code = "ai_invalid_response"
