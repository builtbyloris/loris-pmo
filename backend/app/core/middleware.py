import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
access_logger = logging.getLogger("loris.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if _REQUEST_ID.fullmatch(supplied) else str(uuid4())
        request.state.request_id = request_id
        started = perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        record = {
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "route": route_path,
            "status_code": response.status_code,
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        }
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            record["user_id"] = user_id
        project_id = request.path_params.get("project_id")
        if project_id:
            record["project_id"] = str(project_id)
        access_logger.info("http_request", extra=record)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, production: bool) -> None:
        super().__init__(app)
        self.production = production

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if self.production:
            response.headers.setdefault(
                "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
            )
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


RequestIDMiddleware = RequestContextMiddleware
