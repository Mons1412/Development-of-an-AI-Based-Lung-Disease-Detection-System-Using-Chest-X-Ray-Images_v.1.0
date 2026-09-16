from lung_xray_api.core.config import (
    Settings,
)
from lung_xray_api.infrastructure.persistence.database import (
    build_engine_options,
)


def test_mysql_engine_hardening_options():
    settings = Settings(
        db_password="test-db-password",
        jwt_secret="test-jwt-secret",
        db_connect_timeout_seconds=7,
        db_pool_size=6,
        db_max_overflow=4,
        db_pool_timeout_seconds=21,
        db_pool_recycle_seconds=1800,
        _env_file=None,
    )

    options = build_engine_options(
        settings
    )

    assert (
        options["pool_pre_ping"]
        is True
    )

    assert (
        options["pool_recycle"]
        == 1800
    )

    assert (
        options["pool_size"]
        == 6
    )

    assert (
        options["max_overflow"]
        == 4
    )

    assert (
        options["pool_timeout"]
        == 21
    )

    assert (
        options["connect_args"][
            "connect_timeout"
        ]
        == 7
    )

    assert (
        options["connect_args"][
            "init_command"
        ]
        == "SET time_zone = '+00:00'"
    )
