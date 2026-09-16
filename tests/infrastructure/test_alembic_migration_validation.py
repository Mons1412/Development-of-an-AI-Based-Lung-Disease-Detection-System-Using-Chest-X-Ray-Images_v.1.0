import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pymysql
import pytest
from alembic.config import Config
from alembic.runtime.migration import (
    MigrationContext,
)
from alembic.script import (
    ScriptDirectory,
)
from dotenv import dotenv_values
from sqlalchemy import (
    URL,
    create_engine,
    inspect,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

EXPECTED_BUSINESS_TABLES = {
    "ai_models",
    "analyses",
    "medical_advices",
    "medical_histories",
    "patient_profiles",
    "prediction_probabilities",
    "predictions",
    "reports",
    "users",
}

TEMP_DATABASE_PATTERN = re.compile(
    r"^lungxray_m14_migration_"
    r"[0-9a-f]{12}$"
)


def run_alembic(
    arguments,
    environment,
):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            *arguments,
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )

    if result.returncode != 0:
        pytest.fail(
            "Alembic command failed:\n"
            + " ".join(arguments)
            + "\n\nSTDOUT:\n"
            + result.stdout
            + "\nSTDERR:\n"
            + result.stderr
        )

    return result


def load_test_environment():
    file_values = {
        key: value
        for key, value
        in dotenv_values(
            PROJECT_ROOT / ".env"
        ).items()
        if value is not None
    }

    values = {
        **file_values,
        **os.environ,
    }

    required = [
        "DB_HOST",
        "DB_PORT",
        "DB_ROOT_PASSWORD",
    ]

    missing = [
        key
        for key in required
        if not values.get(key)
    ]

    if missing:
        pytest.fail(
            "Missing required MySQL "
            "test configuration: "
            + ", ".join(missing)
        )

    return values


def create_root_connection(
    values,
):
    return pymysql.connect(
        host=values["DB_HOST"],
        port=int(
            values["DB_PORT"]
        ),
        user="root",
        password=values[
            "DB_ROOT_PASSWORD"
        ],
        charset="utf8mb4",
        connect_timeout=10,
        autocommit=True,
    )


def database_exists(
    connection,
    database_name,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.SCHEMATA
            WHERE SCHEMA_NAME = %s
            """,
            (
                database_name,
            ),
        )

        return (
            cursor.fetchone()[0]
            == 1
        )


def create_temp_database(
    connection,
    database_name,
):
    if not TEMP_DATABASE_PATTERN.fullmatch(
        database_name
    ):
        raise RuntimeError(
            "Unsafe M14 temp database "
            "name."
        )

    if database_exists(
        connection,
        database_name,
    ):
        raise RuntimeError(
            "M14 temp database already "
            "exists."
        )

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE DATABASE
                `{database_name}`
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_0900_ai_ci
            """
        )


def drop_temp_database(
    connection,
    database_name,
):
    if not TEMP_DATABASE_PATTERN.fullmatch(
        database_name
    ):
        raise RuntimeError(
            "REFUSED unsafe database "
            "drop."
        )

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            DROP DATABASE
                `{database_name}`
            """
        )


def build_temp_database_url(
    values,
    database_name,
):
    return URL.create(
        drivername="mysql+pymysql",
        username="root",
        password=values[
            "DB_ROOT_PASSWORD"
        ],
        host=values["DB_HOST"],
        port=int(
            values["DB_PORT"]
        ),
        database=database_name,
        query={
            "charset":
                "utf8mb4",
        },
    )


def build_alembic_environment(
    values,
    database_name,
):
    environment = (
        os.environ.copy()
    )

    environment.update(
        {
            "DB_HOST":
                values["DB_HOST"],
            "DB_PORT":
                values["DB_PORT"],
            "DB_NAME":
                database_name,
            "DB_USER":
                "root",
            "DB_PASSWORD":
                values[
                    "DB_ROOT_PASSWORD"
                ],
            "JWT_SECRET":
                environment.get(
                    "JWT_SECRET",
                    "m14-test-secret",
                ),
        }
    )

    return environment


def get_database_revision(
    engine,
):
    with engine.connect() as connection:
        context = (
            MigrationContext
            .configure(
                connection
            )
        )

        return (
            context
            .get_current_revision()
        )


def get_code_head():
    config = Config(
        str(
            PROJECT_ROOT
            / "alembic.ini"
        )
    )

    script = (
        ScriptDirectory
        .from_config(
            config
        )
    )

    heads = script.get_heads()

    assert len(heads) == 1

    return heads[0]


def test_alembic_offline_sql_does_not_expose_password():
    sentinel = (
        "M14_PASSWORD_MUST_NOT_LEAK"
    )

    environment = (
        os.environ.copy()
    )

    environment.update(
        {
            "DB_HOST":
                "127.0.0.1",
            "DB_PORT":
                "3306",
            "DB_NAME":
                "m14_offline_only",
            "DB_USER":
                "m14_offline_user",
            "DB_PASSWORD":
                sentinel,
            "JWT_SECRET":
                "m14-test-secret",
        }
    )

    result = run_alembic(
        [
            "upgrade",
            "head",
            "--sql",
        ],
        environment,
    )

    combined_output = (
        result.stdout
        + result.stderr
    )

    assert (
        sentinel
        not in combined_output
    )


@pytest.mark.skipif(
    os.getenv(
        "RUN_MYSQL_MIGRATION_TEST"
    ) != "1",
    reason=(
        "MySQL migration lifecycle "
        "requires explicit opt-in."
    ),
)
def test_mysql_alembic_bootstrap_round_trip():
    values = (
        load_test_environment()
    )

    database_name = (
        "lungxray_m14_migration_"
        + uuid.uuid4().hex[:12]
    )

    assert (
        TEMP_DATABASE_PATTERN.fullmatch(
            database_name
        )
    )

    root_connection = (
        create_root_connection(
            values
        )
    )

    temp_engine = None

    print(
        "M14 temporary database:",
        database_name,
    )

    try:
        create_temp_database(
            root_connection,
            database_name,
        )

        assert database_exists(
            root_connection,
            database_name,
        )

        environment = (
            build_alembic_environment(
                values,
                database_name,
            )
        )

        temp_engine = create_engine(
            build_temp_database_url(
                values,
                database_name,
            ),
            pool_pre_ping=True,
        )

        assert (
            inspect(
                temp_engine
            ).get_table_names()
            == []
        )

        run_alembic(
            [
                "upgrade",
                "head",
            ],
            environment,
        )

        tables_after_upgrade = set(
            inspect(
                temp_engine
            ).get_table_names()
        )

        assert (
            EXPECTED_BUSINESS_TABLES
            .issubset(
                tables_after_upgrade
            )
        )

        assert (
            "alembic_version"
            in tables_after_upgrade
        )

        assert (
            get_database_revision(
                temp_engine
            )
            == get_code_head()
        )

        run_alembic(
            [
                "check",
            ],
            environment,
        )

        run_alembic(
            [
                "downgrade",
                "base",
            ],
            environment,
        )

        tables_after_downgrade = set(
            inspect(
                temp_engine
            ).get_table_names()
        )

        assert (
            EXPECTED_BUSINESS_TABLES
            .isdisjoint(
                tables_after_downgrade
            )
        )

        run_alembic(
            [
                "upgrade",
                "head",
            ],
            environment,
        )

        tables_after_second_upgrade = set(
            inspect(
                temp_engine
            ).get_table_names()
        )

        assert (
            EXPECTED_BUSINESS_TABLES
            .issubset(
                tables_after_second_upgrade
            )
        )

        assert (
            "alembic_version"
            in tables_after_second_upgrade
        )

        assert (
            get_database_revision(
                temp_engine
            )
            == get_code_head()
        )

        run_alembic(
            [
                "check",
            ],
            environment,
        )

    finally:
        if temp_engine is not None:
            temp_engine.dispose()

        if database_exists(
            root_connection,
            database_name,
        ):
            drop_temp_database(
                root_connection,
                database_name,
            )

        assert not database_exists(
            root_connection,
            database_name,
        )

        root_connection.close()


def test_initial_migration_downgrade_drops_tables_without_dropping_fk_indexes():
    migration_path = (
        PROJECT_ROOT
        / "migrations"
        / "versions"
        / (
            "826673693392_"
            "create_initial_database_schema.py"
        )
    )

    source = migration_path.read_text(
        encoding="utf-8-sig"
    )

    downgrade_source = source.split(
        "def downgrade() -> None:",
        1,
    )[1]

    assert (
        "op.drop_index"
        not in downgrade_source
    )

    expected_drop_order = [
        "prediction_probabilities",
        "reports",
        "predictions",
        "medical_advices",
        "medical_histories",
        "analyses",
        "patient_profiles",
        "users",
        "ai_models",
    ]

    positions = [
        downgrade_source.index(
            f'"{table_name}"'
        )
        for table_name
        in expected_drop_order
    ]

    assert positions == sorted(
        positions
    )
