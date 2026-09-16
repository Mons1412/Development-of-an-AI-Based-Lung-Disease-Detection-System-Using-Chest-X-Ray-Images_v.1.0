import os

import pytest
from alembic.config import Config
from alembic.runtime.migration import (
    MigrationContext,
)
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from lung_xray_api.infrastructure.persistence.database import (
    engine,
)


pytestmark = pytest.mark.skipif(
    os.getenv(
        "RUN_MYSQL_INTEGRATION"
    ) != "1",
    reason=(
        "MySQL integration tests require "
        "RUN_MYSQL_INTEGRATION=1."
    ),
)


BUSINESS_TABLES = {
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


EXPECTED_FOREIGN_KEYS = {
    "patient_profiles": {
        (
            ("user_id",),
            "users",
            ("id",),
            "CASCADE",
        ),
    },
    "analyses": {
        (
            ("model_id",),
            "ai_models",
            ("id",),
            "RESTRICT",
        ),
        (
            ("patient_id",),
            "patient_profiles",
            ("id",),
            "CASCADE",
        ),
    },
    "medical_histories": {
        (
            ("patient_id",),
            "patient_profiles",
            ("id",),
            "CASCADE",
        ),
    },
    "medical_advices": {
        (
            ("analysis_id",),
            "analyses",
            ("id",),
            "CASCADE",
        ),
    },
    "predictions": {
        (
            ("analysis_id",),
            "analyses",
            ("id",),
            "CASCADE",
        ),
    },
    "reports": {
        (
            ("analysis_id",),
            "analyses",
            ("id",),
            "CASCADE",
        ),
    },
    "prediction_probabilities": {
        (
            ("prediction_id",),
            "predictions",
            ("id",),
            "CASCADE",
        ),
    },
}


EXPECTED_INDEXES = {
    "ai_models": {
        (
            "ix_ai_models_model_key",
            ("model_key",),
            False,
        ),
        (
            "uq_ai_models_key_version",
            (
                "model_key",
                "version",
            ),
            True,
        ),
    },
    "analyses": {
        (
            "ix_analyses_analysis_code",
            ("analysis_code",),
            True,
        ),
        (
            "ix_analyses_model_id",
            ("model_id",),
            False,
        ),
        (
            "ix_analyses_patient_id",
            ("patient_id",),
            False,
        ),
        (
            "ix_analyses_status",
            ("status",),
            False,
        ),
    },
    "medical_advices": {
        (
            "ix_medical_advices_analysis_id",
            ("analysis_id",),
            False,
        ),
    },
    "medical_histories": {
        (
            "ix_medical_histories_patient_id",
            ("patient_id",),
            False,
        ),
    },
    "patient_profiles": {
        (
            "ix_patient_profiles_patient_code",
            ("patient_code",),
            True,
        ),
        (
            "ix_patient_profiles_user_id",
            ("user_id",),
            True,
        ),
    },
    "prediction_probabilities": {
        (
            "ix_prediction_probabilities_prediction_id",
            ("prediction_id",),
            False,
        ),
        (
            "uq_prediction_probability_class",
            (
                "prediction_id",
                "class_name",
            ),
            True,
        ),
    },
    "predictions": {
        (
            "ix_predictions_analysis_id",
            ("analysis_id",),
            True,
        ),
    },
    "reports": {
        (
            "ix_reports_analysis_id",
            ("analysis_id",),
            False,
        ),
        (
            "ix_reports_report_code",
            ("report_code",),
            True,
        ),
    },
    "users": {
        (
            "ix_users_email",
            ("email",),
            True,
        ),
        (
            "ix_users_role",
            ("role",),
            False,
        ),
        (
            "ix_users_username",
            ("username",),
            True,
        ),
    },
}


ORPHAN_CHECKS = [
    (
        "patient_profiles",
        "user_id",
        "users",
        "id",
    ),
    (
        "analyses",
        "patient_id",
        "patient_profiles",
        "id",
    ),
    (
        "analyses",
        "model_id",
        "ai_models",
        "id",
    ),
    (
        "medical_histories",
        "patient_id",
        "patient_profiles",
        "id",
    ),
    (
        "medical_advices",
        "analysis_id",
        "analyses",
        "id",
    ),
    (
        "predictions",
        "analysis_id",
        "analyses",
        "id",
    ),
    (
        "reports",
        "analysis_id",
        "analyses",
        "id",
    ),
    (
        "prediction_probabilities",
        "prediction_id",
        "predictions",
        "id",
    ),
]


def normalize_foreign_key(
    foreign_key,
):
    options = (
        foreign_key.get("options")
        or {}
    )

    ondelete = options.get(
        "ondelete"
    )

    if ondelete is not None:
        ondelete = str(
            ondelete
        ).upper()

    return (
        tuple(
            foreign_key.get(
                "constrained_columns"
            )
            or []
        ),
        foreign_key.get(
            "referred_table"
        ),
        tuple(
            foreign_key.get(
                "referred_columns"
            )
            or []
        ),
        ondelete,
    )


def normalize_index(
    index,
):
    return (
        index.get("name"),
        tuple(
            index.get(
                "column_names"
            )
            or []
        ),
        bool(
            index.get(
                "unique"
            )
        ),
    )


def test_mysql_expected_tables_exist():
    inspector = inspect(
        engine
    )

    tables = set(
        inspector.get_table_names()
    )

    assert (
        BUSINESS_TABLES
        .issubset(tables)
    )

    assert (
        "alembic_version"
        in tables
    )


def test_mysql_foreign_keys_match_contract():
    inspector = inspect(
        engine
    )

    for (
        table,
        expected,
    ) in EXPECTED_FOREIGN_KEYS.items():

        actual = {
            normalize_foreign_key(
                foreign_key
            )
            for foreign_key
            in inspector
            .get_foreign_keys(
                table
            )
        }

        assert actual == expected


def test_mysql_indexes_match_contract():
    inspector = inspect(
        engine
    )

    for (
        table,
        expected,
    ) in EXPECTED_INDEXES.items():

        actual = {
            normalize_index(index)
            for index
            in inspector.get_indexes(
                table
            )
        }

        assert actual == expected


def test_mysql_business_tables_use_innodb_and_utf8mb4():
    with engine.connect() as connection:
        database_name = (
            connection.execute(
                text(
                    "SELECT DATABASE()"
                )
            ).scalar_one()
        )

        rows = connection.execute(
            text(
                """
                SELECT
                    TABLE_NAME,
                    ENGINE,
                    TABLE_COLLATION
                FROM
                    information_schema.TABLES
                WHERE
                    TABLE_SCHEMA = :database_name
                    AND TABLE_NAME !=
                        'alembic_version'
                """
            ),
            {
                "database_name":
                    database_name,
            },
        ).mappings().all()

    actual_tables = {
        row["TABLE_NAME"]
        for row in rows
    }

    assert (
        actual_tables
        == BUSINESS_TABLES
    )

    for row in rows:
        assert (
            str(
                row["ENGINE"]
            ).upper()
            == "INNODB"
        )

        assert str(
            row["TABLE_COLLATION"]
        ).lower().startswith(
            "utf8mb4_"
        )


def test_mysql_alembic_revision_matches_head():
    alembic_config = Config(
        "alembic.ini"
    )

    script = ScriptDirectory.from_config(
        alembic_config
    )

    heads = script.get_heads()

    assert len(heads) == 1

    with engine.connect() as connection:
        context = (
            MigrationContext
            .configure(
                connection
            )
        )

        database_revision = (
            context
            .get_current_revision()
        )

    assert (
        database_revision
        == heads[0]
    )


def test_mysql_has_no_orphaned_foreign_keys():
    with engine.connect() as connection:
        for (
            child_table,
            child_column,
            parent_table,
            parent_column,
        ) in ORPHAN_CHECKS:

            statement = text(
                f"""
                SELECT COUNT(*)
                FROM
                    `{child_table}` AS child
                LEFT JOIN
                    `{parent_table}` AS parent
                ON
                    child.`{child_column}`
                    =
                    parent.`{parent_column}`
                WHERE
                    child.`{child_column}`
                    IS NOT NULL
                    AND
                    parent.`{parent_column}`
                    IS NULL
                """
            )

            orphan_count = (
                connection.execute(
                    statement
                ).scalar_one()
            )

            assert (
                orphan_count == 0
            ), (
                "Orphan rows detected: "
                f"{child_table}."
                f"{child_column}"
                " -> "
                f"{parent_table}."
                f"{parent_column}"
            )
