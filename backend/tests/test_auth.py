from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password, verify_password
from app.repositories.users import UserRepository


async def create_test_user(session: AsyncSession) -> None:
    await UserRepository(session).create(
        email="manager@example.com",
        password_hash=hash_password("correct horse battery staple"),
    )
    await session.commit()


def test_passwords_are_hashed_and_verified() -> None:
    encoded = hash_password("correct horse battery staple")
    assert "correct horse" not in encoded
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


async def test_login_me_logout_flow(client: AsyncClient, session: AsyncSession) -> None:
    await create_test_user(session)

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "MANAGER@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "manager@example.com"
    assert client.cookies.get("loris_access_token")
    csrf = client.cookies.get("loris_csrf_token")
    assert csrf

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "manager@example.com"

    rejected_logout = await client.post("/api/v1/auth/logout")
    assert rejected_logout.status_code == 403
    assert rejected_logout.json()["error"]["code"] == "csrf_failed"

    logout = await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 204
    assert client.cookies.get("loris_access_token") is None


async def test_invalid_credentials_use_consistent_error(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "incorrect"},
    )
    assert response.status_code == 401
    body = response.json()["error"]
    assert body["code"] == "invalid_credentials"
    assert body["request_id"]


async def test_protected_endpoint_rejects_anonymous_user(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
