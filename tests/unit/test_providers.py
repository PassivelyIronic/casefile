import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from casefile.config import Settings
from casefile.providers import (
    ProviderError,
    chat_model_info,
    get_chat_model,
    get_embeddings,
    register_chat,
)
from casefile.providers.fake import FAKE_EMBEDDING_DIM, fake_chat


def test_fake_chat_smoke(fake_settings: Settings) -> None:
    model = get_chat_model(fake_settings)
    assert model.invoke("hello").content == "fake response"


def test_fake_chat_cycles_responses() -> None:
    model = fake_chat(["a", "b"])
    assert [model.invoke("x").content for _ in range(3)] == ["a", "b", "a"]


def test_fake_embeddings_deterministic(fake_settings: Settings) -> None:
    emb = get_embeddings(fake_settings)
    v1, v2 = emb.embed_query("same text"), emb.embed_query("same text")
    assert v1 == v2
    assert len(v1) == FAKE_EMBEDDING_DIM


def test_unknown_providers_raise() -> None:
    with pytest.raises(ProviderError, match="Unknown chat provider"):
        get_chat_model(Settings(chat_provider="nope"))
    with pytest.raises(ProviderError, match="Unknown embedding provider"):
        get_embeddings(Settings(embedding_provider="nope"))


def test_custom_provider_registration() -> None:
    register_chat("custom-test", lambda s: fake_chat([f"custom:{s.chat_model}"]))
    model = get_chat_model(Settings(chat_provider="custom-test", chat_model="m1"))
    assert model.invoke("x").content == "custom:m1"


def test_gemini_requires_key_and_model() -> None:
    with pytest.raises(ProviderError, match="GOOGLE_API_KEY"):
        get_chat_model(Settings(chat_provider="gemini", chat_model="m"))
    with pytest.raises(ProviderError, match="CHAT_MODEL"):
        get_chat_model(Settings(chat_provider="gemini", google_api_key=SecretStr("k")))


def test_gemini_builds_offline() -> None:
    s = Settings(chat_provider="gemini", chat_model="some-model", google_api_key=SecretStr("k"))
    assert isinstance(get_chat_model(s), BaseChatModel)


def test_chat_model_info(fake_settings: Settings) -> None:
    info = chat_model_info(fake_settings)
    assert (info.provider, info.model) == ("fake", "fake")


def test_fake_embedding_type(fake_settings: Settings) -> None:
    assert isinstance(get_embeddings(fake_settings), DeterministicFakeEmbedding)
