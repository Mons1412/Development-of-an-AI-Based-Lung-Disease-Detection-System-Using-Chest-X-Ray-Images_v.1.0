from types import SimpleNamespace

from lung_xray_api.application.services.auth_service import (
    AuthService,
)
from lung_xray_api.core.security import (
    hash_password,
)


PASSWORD = "StrongPassword123!"


class FakeUserRepository:

    def __init__(
        self,
        *,
        phone_users=None,
        username_users=None,
    ):
        self.phone_users = (
            phone_users
            or {}
        )

        self.username_users = (
            username_users
            or {}
        )

        self.phone_calls = []
        self.username_calls = []

    def get_by_phone(
        self,
        db,
        phone,
    ):
        del db

        self.phone_calls.append(
            phone
        )

        return self.phone_users.get(
            phone
        )

    def get_by_username(
        self,
        db,
        username,
    ):
        del db

        self.username_calls.append(
            username
        )

        return self.username_users.get(
            username
        )


def make_user(
    *,
    username="internal_user",
    phone="0901234567",
    role="USER",
    is_active=True,
    password=PASSWORD,
):
    return SimpleNamespace(
        id=1,
        username=username,
        phone=phone,
        role=role,
        is_active=is_active,
        password_hash=hash_password(
            password
        ),
    )


def make_service(
    repository,
):
    service = AuthService()

    service.user_repository = (
        repository
    )

    return service


def test_normalizes_common_vietnam_phone_formats():
    service = AuthService()

    cases = {
        "0901234567": "0901234567",
        "090 123 4567": "0901234567",
        "090-123-4567": "0901234567",
        "+84 901 234 567": "0901234567",
        "84901234567": "0901234567",
    }

    for raw, expected in cases.items():
        assert (
            service.normalize_phone(
                raw
            )
            == expected
        )


def test_user_can_authenticate_by_phone():
    user = make_user()

    repository = FakeUserRepository(
        phone_users={
            "0901234567": user,
        },
    )

    service = make_service(
        repository
    )

    result = service.authenticate_user(
        object(),
        "0901234567",
        PASSWORD,
    )

    assert result is user

    assert repository.phone_calls == [
        "0901234567",
    ]


def test_user_can_authenticate_with_formatted_phone():
    user = make_user()

    repository = FakeUserRepository(
        phone_users={
            "0901234567": user,
        },
    )

    service = make_service(
        repository
    )

    result = service.authenticate_user(
        object(),
        "+84 901 234 567",
        PASSWORD,
    )

    assert result is user


def test_regular_user_cannot_login_with_legacy_username():
    user = make_user(
        username="legacy_user",
        role="USER",
    )

    repository = FakeUserRepository(
        username_users={
            "legacy_user": user,
        },
    )

    service = make_service(
        repository
    )

    result = service.authenticate_user(
        object(),
        "legacy_user",
        PASSWORD,
    )

    assert result is None


def test_legacy_admin_can_login_with_username():
    admin = make_user(
        username="legacy_admin",
        phone=None,
        role="ADMIN",
    )

    repository = FakeUserRepository(
        username_users={
            "legacy_admin": admin,
        },
    )

    service = make_service(
        repository
    )

    result = service.authenticate_user(
        object(),
        "legacy_admin",
        PASSWORD,
    )

    assert result is admin


def test_wrong_password_is_rejected():
    user = make_user()

    repository = FakeUserRepository(
        phone_users={
            "0901234567": user,
        },
    )

    service = make_service(
        repository
    )

    result = service.authenticate_user(
        object(),
        "0901234567",
        "WrongPassword123!",
    )

    assert result is None


def test_inactive_user_is_rejected():
    user = make_user(
        is_active=False
    )

    repository = FakeUserRepository(
        phone_users={
            "0901234567": user,
        },
    )

    service = make_service(
        repository
    )

    result = service.authenticate_user(
        object(),
        "0901234567",
        PASSWORD,
    )

    assert result is None
