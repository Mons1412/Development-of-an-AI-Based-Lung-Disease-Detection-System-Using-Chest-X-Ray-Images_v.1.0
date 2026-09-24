"""add visitor sessions

Revision ID: e7b4c91a2d6f
Revises: a82f4c197e35
"""

from alembic import op
import sqlalchemy as sa


revision = "e7b4c91a2d6f"
down_revision = "a82f4c197e35"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "visitor_sessions",

        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),

        sa.Column(
            "visitor_id",
            sa.String(
                length=36
            ),
            nullable=False,
        ),

        sa.Column(
            "session_id",
            sa.String(
                length=36
            ),
            nullable=False,
        ),

        sa.Column(
            "first_seen_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP"
            ),
        ),

        sa.Column(
            "last_seen_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP"
            ),
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),

        sa.UniqueConstraint(
            "session_id",
            name=(
                "uq_visitor_sessions_session_id"
            ),
        ),
    )

    op.create_index(
        "ix_visitor_sessions_visitor_id",
        "visitor_sessions",
        [
            "visitor_id",
        ],
        unique=False,
    )

    op.create_index(
        "ix_visitor_sessions_last_seen_at",
        "visitor_sessions",
        [
            "last_seen_at",
        ],
        unique=False,
    )


def downgrade() -> None:

    op.drop_index(
        "ix_visitor_sessions_last_seen_at",
        table_name=(
            "visitor_sessions"
        ),
    )

    op.drop_index(
        "ix_visitor_sessions_visitor_id",
        table_name=(
            "visitor_sessions"
        ),
    )

    op.drop_table(
        "visitor_sessions"
    )
