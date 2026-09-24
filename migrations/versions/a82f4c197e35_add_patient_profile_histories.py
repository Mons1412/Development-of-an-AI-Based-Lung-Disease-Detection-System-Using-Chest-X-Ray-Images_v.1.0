"""add patient profile histories

Revision ID: a82f4c197e35
Revises: 1df5d3afc741
"""

from alembic import op
import sqlalchemy as sa


revision = "a82f4c197e35"
down_revision = "1df5d3afc741"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_profile_histories",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "patient_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "height_cm",
            sa.Numeric(
                precision=5,
                scale=2,
            ),
            nullable=True,
        ),

        sa.Column(
            "weight_kg",
            sa.Numeric(
                precision=6,
                scale=2,
            ),
            nullable=True,
        ),

        sa.Column(
            "recorded_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP"
            ),
        ),

        sa.ForeignKeyConstraint(
            [
                "patient_id",
            ],
            [
                "patient_profiles.id",
            ],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    op.create_index(
        "ix_patient_profile_histories_patient_id",
        "patient_profile_histories",
        [
            "patient_id",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_patient_profile_histories_patient_id",
        table_name=(
            "patient_profile_histories"
        ),
    )

    op.drop_table(
        "patient_profile_histories"
    )
