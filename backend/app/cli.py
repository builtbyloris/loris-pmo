import argparse
import asyncio
import getpass
from collections.abc import Sequence

from pydantic import EmailStr, TypeAdapter

from app.auth.passwords import hash_password
from app.core.database import AsyncSessionFactory
from app.repositories.users import UserRepository


async def create_user(email_input: str, password: str) -> None:
    email = str(TypeAdapter(EmailStr).validate_python(email_input)).lower()

    async with AsyncSessionFactory() as session:
        repository = UserRepository(session)
        if await repository.get_by_email(email):
            raise SystemExit("A user with that email already exists.")
        await repository.create(email=email, password_hash=hash_password(password))
        await session.commit()
    print(f"User {email} created.")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Loris PMO administration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create-user", help="Create the initial account")
    create_parser.add_argument("--email")
    args = parser.parse_args(argv)
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
