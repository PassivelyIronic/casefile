import pytest

from casefile.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests never see the developer's environment or `.env`."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()


@pytest.fixture
def fake_settings() -> Settings:
    return Settings(chat_provider="fake", chat_model="fake", embedding_provider="fake")
