from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from lung_xray_api.core.config import settings


def build_engine_options(
    app_settings=settings,
) -> dict:
    return {
        "pool_pre_ping": True,
        "pool_recycle":
            app_settings
            .db_pool_recycle_seconds,
        "pool_size":
            app_settings.db_pool_size,
        "max_overflow":
            app_settings.db_max_overflow,
        "pool_timeout":
            app_settings
            .db_pool_timeout_seconds,
        "connect_args": {
            "connect_timeout":
                app_settings
                .db_connect_timeout_seconds,
            "init_command":
                "SET time_zone = '+00:00'",
        },
    }


engine = create_engine(
    settings.database_url,
    **build_engine_options(),
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

def check_database_connection() -> bool:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return result.scalar() == 1