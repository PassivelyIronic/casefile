import pytest

from casefile.config import Settings
from casefile.providers import get_chat_model, get_embeddings

BGE_M3_DIM = 1024


@pytest.mark.integration
def test_ollama_bge_m3_embedding() -> None:
    settings = Settings(embedding_provider="ollama")
    vec = get_embeddings(settings).embed_query("My credit report shows an account I never opened.")
    assert len(vec) == BGE_M3_DIM


@pytest.mark.llm
def test_real_chat_provider_replies() -> None:
    settings = Settings()
    reply = get_chat_model(settings).invoke("Reply with the single word OK.")
    assert "ok" in str(reply.content).lower()
