from httpx import AsyncClient

from app.main import create_app


def test_application_factory_starts() -> None:
    app = create_app()
    assert app.title == "Loris PMO"


async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


async def test_database_readiness_endpoint(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
