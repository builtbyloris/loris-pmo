import json
import logging
from datetime import UTC, datetime

from app.core.config import Settings

_runtime_defaults: dict[str, tuple[list[logging.Handler], int, bool]] = {}


class RuntimeExceptionFilter(logging.Filter):
    """Redact runtime exception payloads before any production handler sees them."""

    def filter(self, record: logging.LogRecord) -> bool:
        exception = record.exc_info[1] if record.exc_info else None
        if exception is None and isinstance(record.msg, BaseException):
            exception = record.msg
        # Uvicorn lifespan failures can arrive as an already-formatted traceback.
        formatted_traceback = "Traceback (most recent call last)" in str(record.msg)
        if exception is not None or record.exc_info or formatted_traceback or record.exc_text:
            record.msg = "runtime_exception"
            record.args = ()
            record.exception_type = type(exception).__name__ if exception else "RuntimeFailure"
            if isinstance(exception, OSError) and exception.errno is not None:
                record.errno = exception.errno
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for field in (
            "request_id",
            "method",
            "route",
            "status_code",
            "duration_ms",
            "user_id",
            "project_id",
            "exception_type",
            "errno",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler()
    if settings.app_env == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("loris")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False

    # Uvicorn logs ASGI exceptions again after FastAPI has returned its safe 500.
    # Handle runtime loggers explicitly; do not disable startup/shutdown/bind errors.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "asyncio"):
        runtime = logging.getLogger(name)
        runtime.filters[:] = [
            item for item in runtime.filters if not isinstance(item, RuntimeExceptionFilter)
        ]
        if settings.app_env == "production":
            if name not in _runtime_defaults:
                _runtime_defaults[name] = (runtime.handlers[:], runtime.level, runtime.propagate)
            runtime.addFilter(RuntimeExceptionFilter())
            runtime.handlers[:] = [handler]
            runtime.setLevel(level)
            runtime.propagate = False
        elif name in _runtime_defaults:
            runtime.handlers, runtime.level, runtime.propagate = _runtime_defaults.pop(name)
