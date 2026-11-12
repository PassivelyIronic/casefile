"""All runtime configuration, read from environment / `.env` in one place."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    chat_provider: str = "gemini"
    chat_model: str = ""
    google_api_key: SecretStr | None = None

    embedding_provider: str = "ollama"
    embedding_model: str = "bge-m3"
    ollama_base_url: str = "http://localhost:11434"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "casefile"
    postgres_user: str = "casefile"
    postgres_password: SecretStr = SecretStr("casefile")

    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    hf_token: SecretStr | None = None

    casefile_seed: int = 42
    log_level: str = "INFO"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
