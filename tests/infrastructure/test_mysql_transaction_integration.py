import json
import os
import re
import subprocess
import sys
import threading
import uuid
from concurrent.futures import (
    ThreadPoolExecutor,
)
from decimal import Decimal
from pathlib import Path

import pymysql
import pytest
from dotenv import dotenv_values
from sqlalchemy import (
    URL,
    create_engine,
    text,
)
from sqlalchemy.exc import IntegrityError


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

TEMP_DATABASE_PATTERN = re.compile(
    r"^lungxray_m14_integration_"
    r"[0-9a-f]{12}$"
)


pytestmark = pytest.mark.skipif(
    os.getenv(
        "RUN_MYSQL_INTEGRATION"
    ) != "1",
    reason=(
        "MySQL integration tests "
        "require "
        "RUN_MYSQL_INTEGRATION=1."
    ),
)


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
            "Missing MySQL integration "
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


def create_temp_database(
    connection,
    database_name,
):
    if not TEMP_DATABASE_PATTERN.fullmatch(
        database_name
    ):
        raise RuntimeError(
            "Unsafe integration database "
            "name."
        )

    if database_exists(
        connection,
        database_name,
    ):
        raise RuntimeError(
            "Integration database "
            "already exists."
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


def build_database_url(
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
                    "m14-integration-secret",
                ),
        }
    )

    return environment


def run_alembic_upgrade(
    environment,
):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
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
            "Alembic upgrade failed.\n"
            "STDOUT:\n"
            + result.stdout
            + "\nSTDERR:\n"
            + result.stderr
        )


@pytest.fixture(
    scope="module"
)
def mysql_engine():
    values = (
        load_test_environment()
    )

    database_name = (
        "lungxray_m14_integration_"
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

    engine = None

    print(
        "M14 integration database:",
        database_name,
    )

    try:
        create_temp_database(
            root_connection,
            database_name,
        )

        environment = (
            build_alembic_environment(
                values,
                database_name,
            )
        )

        run_alembic_upgrade(
            environment
        )

        engine = create_engine(
            build_database_url(
                values,
                database_name,
            ),
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=1,
            pool_timeout=5,
            pool_recycle=3600,
            connect_args={
                "connect_timeout": 10,
                "init_command":
                    "SET time_zone = '+00:00'",
            },
        )

        yield engine

    finally:
        if engine is not None:
            engine.dispose()

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


def make_suffix():
    return uuid.uuid4().hex[:12]


def insert_user(
    connection,
    suffix,
):
    result = connection.execute(
        text(
            """
            INSERT INTO users (
                username,
                email,
                password_hash,
                role,
                is_active
            )
            VALUES (
                :username,
                :email,
                :password_hash,
                :role,
                :is_active
            )
            """
        ),
        {
            "username":
                f"user_{suffix}",
            "email":
                f"{suffix}@example.com",
            "password_hash":
                "integration-test-hash",
            "role":
                "USER",
            "is_active":
                True,
        },
    )

    return result.lastrowid


def insert_model(
    connection,
    suffix,
):
    result = connection.execute(
        text(
            """
            INSERT INTO ai_models (
                model_key,
                display_name,
                architecture,
                version,
                artifact_path,
                class_names,
                is_active,
                is_default
            )
            VALUES (
                :model_key,
                :display_name,
                :architecture,
                :version,
                :artifact_path,
                :class_names,
                :is_active,
                :is_default
            )
            """
        ),
        {
            "model_key":
                f"model_{suffix}",
            "display_name":
                f"Model {suffix}",
            "architecture":
                "IntegrationNet",
            "version":
                "1.0.0",
            "artifact_path":
                f"test/{suffix}.keras",
            "class_names":
                json.dumps(
                    [
                        "normal",
                        "pneumonia",
                        "tuberculosis",
                    ]
                ),
            "is_active":
                True,
            "is_default":
                False,
        },
    )

    return result.lastrowid


def insert_patient(
    connection,
    user_id,
    suffix,
):
    result = connection.execute(
        text(
            """
            INSERT INTO patient_profiles (
                user_id,
                patient_code,
                full_name
            )
            VALUES (
                :user_id,
                :patient_code,
                :full_name
            )
            """
        ),
        {
            "user_id":
                user_id,
            "patient_code":
                f"PX{suffix}",
            "full_name":
                "M14 Integration Patient",
        },
    )

    return result.lastrowid


def insert_analysis(
    connection,
    patient_id,
    model_id,
    suffix,
):
    result = connection.execute(
        text(
            """
            INSERT INTO analyses (
                analysis_code,
                patient_id,
                model_id,
                input_source,
                original_filename,
                stored_image_path,
                status
            )
            VALUES (
                :analysis_code,
                :patient_id,
                :model_id,
                :input_source,
                :original_filename,
                :stored_image_path,
                :status
            )
            """
        ),
        {
            "analysis_code":
                f"AN-{suffix}",
            "patient_id":
                patient_id,
            "model_id":
                model_id,
            "input_source":
                "UPLOAD",
            "original_filename":
                f"{suffix}.png",
            "stored_image_path":
                f"test/{suffix}.png",
            "status":
                "COMPLETED",
        },
    )

    return result.lastrowid


def test_mysql_commit_and_rollback(
    mysql_engine,
):
    committed_suffix = (
        make_suffix()
    )

    rolled_back_suffix = (
        make_suffix()
    )

    with mysql_engine.begin() as connection:
        insert_user(
            connection,
            committed_suffix,
        )

    with mysql_engine.connect() as connection:
        transaction = (
            connection.begin()
        )

        insert_user(
            connection,
            rolled_back_suffix,
        )

        transaction.rollback()

    with mysql_engine.connect() as connection:
        committed_count = (
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM users
                    WHERE username = :username
                    """
                ),
                {
                    "username":
                        f"user_{committed_suffix}",
                },
            ).scalar_one()
        )

        rolled_back_count = (
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM users
                    WHERE username = :username
                    """
                ),
                {
                    "username":
                        f"user_{rolled_back_suffix}",
                },
            ).scalar_one()
        )

    assert committed_count == 1
    assert rolled_back_count == 0


def test_mysql_unique_constraint_is_enforced(
    mysql_engine,
):
    suffix = make_suffix()

    with mysql_engine.begin() as connection:
        insert_user(
            connection,
            suffix,
        )

    with pytest.raises(
        IntegrityError
    ):
        with mysql_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO users (
                        username,
                        email,
                        password_hash,
                        role,
                        is_active
                    )
                    VALUES (
                        :username,
                        :email,
                        :password_hash,
                        :role,
                        :is_active
                    )
                    """
                ),
                {
                    "username":
                        f"user_{suffix}",
                    "email":
                        f"duplicate_{suffix}"
                        "@example.com",
                    "password_hash":
                        "integration-test-hash",
                    "role":
                        "USER",
                    "is_active":
                        True,
                },
            )


def test_mysql_foreign_key_is_enforced(
    mysql_engine,
):
    suffix = make_suffix()

    with pytest.raises(
        IntegrityError
    ):
        with mysql_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO patient_profiles (
                        user_id,
                        patient_code,
                        full_name
                    )
                    VALUES (
                        :user_id,
                        :patient_code,
                        :full_name
                    )
                    """
                ),
                {
                    "user_id":
                        2147483646,
                    "patient_code":
                        f"PX{suffix}",
                    "full_name":
                        "Invalid FK Patient",
                },
            )


def test_mysql_cascade_delete_removes_dependents(
    mysql_engine,
):
    suffix = make_suffix()

    with mysql_engine.begin() as connection:
        user_id = insert_user(
            connection,
            suffix,
        )

        model_id = insert_model(
            connection,
            suffix,
        )

        patient_id = insert_patient(
            connection,
            user_id,
            suffix,
        )

        connection.execute(
            text(
                """
                INSERT INTO medical_histories (
                    patient_id
                )
                VALUES (
                    :patient_id
                )
                """
            ),
            {
                "patient_id":
                    patient_id,
            },
        )

        analysis_id = insert_analysis(
            connection,
            patient_id,
            model_id,
            suffix,
        )

        prediction_result = (
            connection.execute(
                text(
                    """
                    INSERT INTO predictions (
                        analysis_id,
                        predicted_class,
                        confidence
                    )
                    VALUES (
                        :analysis_id,
                        :predicted_class,
                        :confidence
                    )
                    """
                ),
                {
                    "analysis_id":
                        analysis_id,
                    "predicted_class":
                        "normal",
                    "confidence":
                        Decimal(
                            "0.9000000"
                        ),
                },
            )
        )

        prediction_id = (
            prediction_result.lastrowid
        )

        connection.execute(
            text(
                """
                INSERT INTO
                    prediction_probabilities (
                        prediction_id,
                        class_name,
                        probability
                    )
                VALUES (
                    :prediction_id,
                    :class_name,
                    :probability
                )
                """
            ),
            {
                "prediction_id":
                    prediction_id,
                "class_name":
                    "normal",
                "probability":
                    Decimal(
                        "0.9000000"
                    ),
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO medical_advices (
                    analysis_id,
                    language,
                    provider,
                    advice_text
                )
                VALUES (
                    :analysis_id,
                    :language,
                    :provider,
                    :advice_text
                )
                """
            ),
            {
                "analysis_id":
                    analysis_id,
                "language":
                    "en",
                "provider":
                    "integration-test",
                "advice_text":
                    "Temporary test advice.",
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO reports (
                    analysis_id,
                    report_code,
                    language,
                    file_path
                )
                VALUES (
                    :analysis_id,
                    :report_code,
                    :language,
                    :file_path
                )
                """
            ),
            {
                "analysis_id":
                    analysis_id,
                "report_code":
                    f"RP-{suffix}",
                "language":
                    "en",
                "file_path":
                    f"test/{suffix}.pdf",
            },
        )

    with mysql_engine.begin() as connection:
        connection.execute(
            text(
                """
                DELETE FROM users
                WHERE id = :user_id
                """
            ),
            {
                "user_id":
                    user_id,
            },
        )

    checks = [
        (
            "patient_profiles",
            "id",
            patient_id,
        ),
        (
            "medical_histories",
            "patient_id",
            patient_id,
        ),
        (
            "analyses",
            "id",
            analysis_id,
        ),
        (
            "predictions",
            "id",
            prediction_id,
        ),
        (
            "prediction_probabilities",
            "prediction_id",
            prediction_id,
        ),
        (
            "medical_advices",
            "analysis_id",
            analysis_id,
        ),
        (
            "reports",
            "analysis_id",
            analysis_id,
        ),
    ]

    with mysql_engine.connect() as connection:
        for (
            table_name,
            column_name,
            value,
        ) in checks:

            count = connection.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM `{table_name}`
                    WHERE `{column_name}` = :value
                    """
                ),
                {
                    "value":
                        value,
                },
            ).scalar_one()

            assert (
                count == 0
            ), table_name

        model_count = (
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM ai_models
                    WHERE id = :model_id
                    """
                ),
                {
                    "model_id":
                        model_id,
                },
            ).scalar_one()
        )

    assert model_count == 1


def test_mysql_decimal_precision_is_preserved(
    mysql_engine,
):
    suffix = make_suffix()

    expected_confidence = Decimal(
        "0.1234567"
    )

    expected_probability = Decimal(
        "0.7654321"
    )

    with mysql_engine.begin() as connection:
        user_id = insert_user(
            connection,
            suffix,
        )

        model_id = insert_model(
            connection,
            suffix,
        )

        patient_id = insert_patient(
            connection,
            user_id,
            suffix,
        )

        analysis_id = insert_analysis(
            connection,
            patient_id,
            model_id,
            suffix,
        )

        prediction_result = (
            connection.execute(
                text(
                    """
                    INSERT INTO predictions (
                        analysis_id,
                        predicted_class,
                        confidence
                    )
                    VALUES (
                        :analysis_id,
                        :predicted_class,
                        :confidence
                    )
                    """
                ),
                {
                    "analysis_id":
                        analysis_id,
                    "predicted_class":
                        "pneumonia",
                    "confidence":
                        expected_confidence,
                },
            )
        )

        prediction_id = (
            prediction_result.lastrowid
        )

        connection.execute(
            text(
                """
                INSERT INTO
                    prediction_probabilities (
                        prediction_id,
                        class_name,
                        probability
                    )
                VALUES (
                    :prediction_id,
                    :class_name,
                    :probability
                )
                """
            ),
            {
                "prediction_id":
                    prediction_id,
                "class_name":
                    "pneumonia",
                "probability":
                    expected_probability,
            },
        )

    with mysql_engine.connect() as connection:
        confidence = (
            connection.execute(
                text(
                    """
                    SELECT confidence
                    FROM predictions
                    WHERE id = :prediction_id
                    """
                ),
                {
                    "prediction_id":
                        prediction_id,
                },
            ).scalar_one()
        )

        probability = (
            connection.execute(
                text(
                    """
                    SELECT probability
                    FROM prediction_probabilities
                    WHERE prediction_id =
                        :prediction_id
                    """
                ),
                {
                    "prediction_id":
                        prediction_id,
                },
            ).scalar_one()
        )

    assert (
        confidence
        == expected_confidence
    )

    assert (
        probability
        == expected_probability
    )


def test_mysql_pool_supports_three_concurrent_connections(
    mysql_engine,
):
    barrier = threading.Barrier(
        3
    )

    def worker():
        with mysql_engine.connect() as connection:
            connection_id = (
                connection.execute(
                    text(
                        "SELECT CONNECTION_ID()"
                    )
                ).scalar_one()
            )

            timezone = (
                connection.execute(
                    text(
                        "SELECT @@session.time_zone"
                    )
                ).scalar_one()
            )

            probe = (
                connection.execute(
                    text(
                        "SELECT 1"
                    )
                ).scalar_one()
            )

            barrier.wait(
                timeout=10
            )

            return (
                connection_id,
                timezone,
                probe,
            )

    with ThreadPoolExecutor(
        max_workers=3
    ) as executor:
        results = list(
            executor.map(
                lambda _:
                    worker(),
                range(3),
            )
        )

    connection_ids = {
        result[0]
        for result in results
    }

    assert len(
        connection_ids
    ) == 3

    assert all(
        result[1] == "+00:00"
        for result in results
    )

    assert all(
        result[2] == 1
        for result in results
    )
