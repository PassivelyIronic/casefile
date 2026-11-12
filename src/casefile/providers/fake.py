"""Offline providers for unit tests: no network, no keys, deterministic."""

from collections.abc import Iterator

from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from casefile.config import Settings

FAKE_EMBEDDING_DIM = 1024  # same as bge-m3


def _replies(responses: list[str]) -> Iterator[AIMessage]:
    while True:
        yield from (AIMessage(content=r) for r in responses)


def fake_chat(responses: list[str]) -> BaseChatModel:
    """Fake chat model that cycles through `responses`."""
    return GenericFakeChatModel(messages=_replies(responses))


def create_chat(settings: Settings) -> BaseChatModel:
    return fake_chat(["fake response"])


def create_embeddings(settings: Settings) -> Embeddings:
    return DeterministicFakeEmbedding(size=FAKE_EMBEDDING_DIM)
