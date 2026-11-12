import pytest
from pydantic import SecretStr

from casefile.config import Settings


def test_defaults_without_env() -> None:
    s = Settings()
    assert s.chat_provider == "gemini"
    assert s.embedding_model == "bge-m3"
    assert s.google_api_key is None


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAT_PROVIDER", "fake")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    s = Settings()
    assert s.chat_provider == "fake"
    assert s.postgres_port == 6543


def test_secrets_are_masked() -> None:
    s = Settings(google_api_key=SecretStr("sk-test"))
    assert "sk-test" not in repr(s)


def test_postgres_dsn() -> None:
    s = Settings(postgres_user="u", postgres_password=SecretStr("p"), postgres_db="d")
    assert s.postgres_dsn == "postgresql://u:p@localhost:5432/d"
