import argparse
import asyncio
import getpass
import json
from collections.abc import Sequence

from pydantic import EmailStr, TypeAdapter
from sqlalchemy.engine import make_url

from app.auth.passwords import hash_password
from app.core.config import get_settings
from app.repositories.users import UserRepository


async def create_user(email_input: str, password: str) -> None:
    from app.core.database import AsyncSessionFactory

    email = str(TypeAdapter(EmailStr).validate_python(email_input)).lower()
    async with AsyncSessionFactory() as session:
        repository = UserRepository(session)
        if await repository.get_by_email(email):
            raise SystemExit("A user with that email already exists.")
        await repository.create(email=email, password_hash=hash_password(password))
        await session.commit()
    print(f"User {email} created.")


def check_config() -> None:
    settings = get_settings()
    database = make_url(settings.database_url)
    summary = {
        "status": "valid",
        "environment": settings.app_env,
        "database_driver": database.drivername,
        "database_host_configured": bool(database.host),
        "cors_origin_count": len(settings.allowed_origins),
        "trusted_host_count": len(settings.allowed_hosts),
        "secure_cookies": settings.secure_cookies,
        "document_storage_backend": settings.document_storage_backend,
        "ai_configured": bool(settings.gemini_api_key),
        "google_oauth_configured": bool(settings.google_oauth_client_id),
        "github_oauth_configured": bool(settings.github_oauth_client_id),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Loris PMO administration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create-user", help="Create the initial account")
    create_parser.add_argument("--email")
    subparsers.add_parser("check-config", help="Validate configuration without exposing secrets")
    args = parser.parse_args(argv)
    if args.command == "check-config":
        check_config()
        return
    if args.command == "create-user":
        email = args.email or input("Email: ").strip()
        password = getpass.getpass("Password (minimum 12 characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if len(password) < 12:
            raise SystemExit("Password must contain at least 12 characters.")
        if password != confirmation:
            raise SystemExit("Passwords do not match.")
        asyncio.run(create_user(email, password))


if __name__ == "__main__":
    main()
