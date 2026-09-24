import hashlib
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

import pymysql
import pytest
from dotenv import dotenv_values
from sqlalchemy import (
    URL,
    create_engine,
    inspect,
    text,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

COMPOSE_PATH = (
    PROJECT_ROOT
    / "docker-compose.yml"
)

CONTAINER_NAME = (
    "lungxray2-mysql"
)

SOURCE_DATABASE = (
    "lungxray"
)

RESTORE_DATABASE_PATTERN = re.compile(
    r"^lungxray_m14_restore_"
    r"[0-9a-f]{12}$"
)


def test_mysql_compose_hardening_contract():
    compose = COMPOSE_PATH.read_text(
        encoding="utf-8-sig"
    )

    assert (
        "image: mysql:8.4.11"
        in compose
    )

    assert (
        '"127.0.0.1:3306:3306"'
        in compose
    )

    assert (
        "lungxray2_mysql_data:"
        "/var/lib/mysql"
        in compose
    )

    assert (
        "restart: unless-stopped"
        in compose
    )

    health_start = compose.index(
        "    healthcheck:"
    )

    health_end = compose.index(
        "    restart:",
        health_start,
    )

    health_block = compose[
        health_start:health_end
    ]

    assert (
        "MYSQL_ROOT_PASSWORD"
        not in health_block
    )

    assert (
        "MYSQL_PASSWORD"
        not in health_block
    )

    assert (
        '"CMD"'
        in health_block
    )

    assert (
        '"mysqladmin"'
        in health_block
    )

    assert (
        '"ping"'
        in health_block
    )

    assert (
        '"127.0.0.1"'
        in health_block
    )


def load_environment():
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
            "Missing backup/restore "
            "configuration: "
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


def create_restore_database(
    connection,
    database_name,
):
    if not (
        RESTORE_DATABASE_PATTERN
        .fullmatch(
            database_name
        )
    ):
        raise RuntimeError(
            "Unsafe restore database "
            "name."
        )

    if database_exists(
        connection,
        database_name,
    ):
        raise RuntimeError(
            "Restore database already "
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


def drop_restore_database(
    connection,
    database_name,
):
    if not (
        RESTORE_DATABASE_PATTERN
        .fullmatch(
            database_name
        )
    ):
        raise RuntimeError(
            "REFUSED unsafe restore "
            "database drop."
        )

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            DROP DATABASE
                `{database_name}`
            """
        )


def build_root_url(
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


def exact_table_counts(
    engine,
):
    inspector = inspect(
        engine
    )

    tables = sorted(
        inspector.get_table_names()
    )

    counts = {}

    with engine.connect() as connection:
        for table_name in tables:
            counts[
                table_name
            ] = int(
                connection.execute(
                    text(
                        "SELECT COUNT(*) "
                        f"FROM `{table_name}`"
                    )
                ).scalar_one()
            )

    return counts


def alembic_revision(
    engine,
):
    with engine.connect() as connection:
        return connection.execute(
            text(
                """
                SELECT version_num
                FROM alembic_version
                """
            )
        ).scalar_one()


def run_dump(
    output_path,
):
    command = [
        "docker",
        "exec",
        CONTAINER_NAME,
        "sh",
        "-lc",
        (
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" '
            "exec mysqldump "
            "-uroot "
            "--single-transaction "
            "--quick "
            "--no-tablespaces "
            "--hex-blob "
            "--set-gtid-purged=OFF "
            "--default-character-set=utf8mb4 "
            "--skip-comments "
            "--skip-dump-date "
            + SOURCE_DATABASE
        ),
    ]

    with output_path.open(
        "wb"
    ) as output:
        result = subprocess.run(
            command,
            stdout=output,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )

    if result.returncode != 0:
        pytest.fail(
            "mysqldump failed:\n"
            + result.stderr.decode(
                "utf-8",
                errors="replace",
            )
        )


def restore_dump(
    input_path,
    database_name,
):
    if not (
        RESTORE_DATABASE_PATTERN
        .fullmatch(
            database_name
        )
    ):
        raise RuntimeError(
            "Unsafe restore database "
            "name."
        )

    command = [
        "docker",
        "exec",
        "-i",
        CONTAINER_NAME,
        "sh",
        "-lc",
        (
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" '
            "exec mysql "
            "-uroot "
            "--default-character-set=utf8mb4 "
            + database_name
        ),
    ]

    with input_path.open(
        "rb"
    ) as input_file:
        result = subprocess.run(
            command,
            stdin=input_file,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )

    if result.returncode != 0:
        pytest.fail(
            "MySQL restore failed:\n"
            + result.stderr.decode(
                "utf-8",
                errors="replace",
            )
        )


@pytest.mark.skipif(
    os.getenv(
        "RUN_MYSQL_BACKUP_RESTORE"
    ) != "1",
    reason=(
        "Backup/restore smoke test "
        "requires explicit opt-in."
    ),
)
def test_mysql_backup_restore_round_trip():
    from lung_xray_api.infrastructure.persistence.database import (
        engine as source_engine,
    )

    values = load_environment()

    with source_engine.connect() as connection:
        source_database = (
            connection.execute(
                text(
                    "SELECT DATABASE()"
                )
            ).scalar_one()
        )

    assert (
        source_database
        == SOURCE_DATABASE
    )

    source_tables = set(
        inspect(
            source_engine
        ).get_table_names()
    )

    source_counts_before = (
        exact_table_counts(
            source_engine
        )
    )

    source_revision = (
        alembic_revision(
            source_engine
        )
    )

    restore_database = (
        "lungxray_m14_restore_"
        + uuid.uuid4().hex[:12]
    )

    assert (
        RESTORE_DATABASE_PATTERN
        .fullmatch(
            restore_database
        )
    )

    root_connection = (
        create_root_connection(
            values
        )
    )

    restore_engine = None

    print(
        "M14 restore database:",
        restore_database,
    )

    try:
        create_restore_database(
            root_connection,
            restore_database,
        )

        with tempfile.TemporaryDirectory(
            prefix=(
                "lungxray_m14_backup_"
            )
        ) as temp_directory:

            backup_path = (
                Path(
                    temp_directory
                )
                / "lungxray.sql"
            )

            run_dump(
                backup_path
            )

            backup_bytes = (
                backup_path
                .read_bytes()
            )

            assert len(
                backup_bytes
            ) > 0

            digest = (
                hashlib.sha256(
                    backup_bytes
                ).hexdigest()
            )

            print(
                "Backup bytes:",
                len(
                    backup_bytes
                ),
            )

            print(
                "Backup SHA256:",
                digest,
            )

            dump_upper = (
                backup_bytes
                .upper()
            )

            assert (
                b"CREATE DATABASE"
                not in dump_upper
            )

            assert (
                b"USE `LUNGXRAY`"
                not in dump_upper
            )

            source_counts_after = (
                exact_table_counts(
                    source_engine
                )
            )

            assert (
                source_counts_after
                == source_counts_before
            )

            restore_dump(
                backup_path,
                restore_database,
            )

            restore_engine = (
                create_engine(
                    build_root_url(
                        values,
                        restore_database,
                    ),
                    pool_pre_ping=True,
                    connect_args={
                        "connect_timeout":
                            10,
                    },
                )
            )

            restored_tables = set(
                inspect(
                    restore_engine
                ).get_table_names()
            )

            assert (
                restored_tables
                == source_tables
            )

            restored_counts = (
                exact_table_counts(
                    restore_engine
                )
            )

            assert (
                restored_counts
                == source_counts_before
            )

            assert (
                alembic_revision(
                    restore_engine
                )
                == source_revision
            )

    finally:
        if restore_engine is not None:
            restore_engine.dispose()

        if database_exists(
            root_connection,
            restore_database,
        ):
            drop_restore_database(
                root_connection,
                restore_database,
            )

        assert not database_exists(
            root_connection,
            restore_database,
        )

        root_connection.close()
