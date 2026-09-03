"""Test-only Uvicorn factory; never included in the application image/package."""


def create_probe_app():
    from app.main import create_app

    application = create_app()

    @application.get("/forced-error")
    async def forced_error():
        raise RuntimeError("VERY_SECRET_EXCEPTION_MARKER")

    return application
