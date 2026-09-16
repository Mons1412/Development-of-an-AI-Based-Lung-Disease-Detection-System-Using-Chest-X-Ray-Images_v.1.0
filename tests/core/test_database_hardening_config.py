import pytest
from pydantic import ValidationError

from lung_xray_api.core.config import Settings


def make_settings(**overrides):
    values = {
        "db_password": "test-db-password",
        "jwt_secret": "test-jwt-secret",
    }

    values.update(overrides)

    return Settings(
        **values,
        _env_file=None,
    )


def test_database_hardening_defaults():
    settings = make_settings()

    assert (
        settings.db_connect_timeout_seconds
        == 10
    )

    assert (
        settings.db_pool_size
        == 5
    )

    assert (
        settings.db_max_overflow
        == 10
    )

    assert (
        settings.db_pool_timeout_seconds
        == 30
    )

    assert (
        settings.db_pool_recycle_seconds
        == 3600
    )


@pytest.mark.parametrize(
    (
        "field_name",
        "invalid_value",
    ),
    [
        (
            "db_connect_timeout_seconds",
            0,
        ),
        (
            "db_pool_size",
            0,
        ),
        (
            "db_max_overflow",
            -1,
        ),
        (
            "db_pool_timeout_seconds",
            0,
        ),
        (
            "db_pool_recycle_seconds",
            0,
        ),
    ],
)
def test_invalid_database_hardening_values_are_rejected(
    field_name,
    invalid_value,
):
    with pytest.raises(
        ValidationError
    ):
        make_settings(
            **{
                field_name:
                    invalid_value,
            }
        )
