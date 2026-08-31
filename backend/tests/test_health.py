from httpx import AsyncClient

from app.main import create_app
from app.version import RELEASE_DATE, RELEASE_STATUS, __version__


def test_application_factory_starts() -> None:
    app = create_app()
    assert app.title == "Loris PMO"
    assert app.version == __version__ == "1.0.0"
    assert RELEASE_DATE == "2026-08-31"
    assert RELEASE_STATUS == "V1"


async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}
    assert response.headers["X-Request-ID"]


async def test_database_readiness_endpoint(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
