from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    app_name: str = "LungXrayAI2"
    app_env: str = "development"

    host: str = "127.0.0.1"
    port: int = 8000

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "lungxray"
    db_user: str = "lungxray"
    db_password: str

    db_connect_timeout_seconds: int = Field(
        default=10,
        gt=0,
    )
    db_pool_size: int = Field(
        default=5,
        gt=0,
    )
    db_max_overflow: int = Field(
        default=10,
        ge=0,
    )
    db_pool_timeout_seconds: int = Field(
        default=30,
        gt=0,
    )
    db_pool_recycle_seconds: int = Field(
        default=3600,
        gt=0,
    )

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
