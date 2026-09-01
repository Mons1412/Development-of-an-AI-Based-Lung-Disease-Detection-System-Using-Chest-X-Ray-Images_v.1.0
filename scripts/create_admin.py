import getpass

from lung_xray_api.core.security import hash_password
from lung_xray_api.infrastructure.persistence.database import SessionLocal
from lung_xray_api.infrastructure.persistence.orm import UserModel
from lung_xray_api.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)


def main() -> None:
    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password: ")

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    repository = UserRepository()
    db = SessionLocal()

    try:
        if repository.get_by_username(db, username):
            print("Username already exists.")
            return

        if repository.get_by_email(db, email):
            print("Email already exists.")
            return

        admin = repository.create(
            db,
            username=username,
            email=email,
            password_hash=hash_password(password),
            role="ADMIN",
        )

        print(
            f"Admin created: "
            f"id={admin.id}, "
            f"username={admin.username}, "
            f"role={admin.role}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()