import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger("loris.errors")


def _payload(request: Request, code: str, message: str, details: Any = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(request, exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
            for item in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_payload(request, "validation_error", "Request validation failed.", details),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        if get_settings().app_env == "production":
            logger.error(
                "unhandled_application_error",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "exception_type": type(exc).__name__,
                },
            )
        else:
            logger.exception("Unhandled application error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_payload(
                request,
                "internal_error",
                "An unexpected error occurred. Please try again.",
            ),
        )
