"""Provider registry.

Chat and embedding providers are registered by name and created from `Settings`.
Built-in providers are referenced as import paths and loaded lazily, so a provider's
SDK is imported only when that provider is selected.

Adding a provider: write a factory `(Settings) -> BaseChatModel` (or `-> Embeddings`)
and either add it to the built-in table or call `register_chat` / `register_embedding`.
Then select it with `CHAT_PROVIDER=<name>` / `EMBEDDING_PROVIDER=<name>`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from casefile.config import Settings, get_settings

ChatFactory = Callable[[Settings], BaseChatModel]
EmbeddingFactory = Callable[[Settings], Embeddings]

_BUILTIN_CHAT: dict[str, str] = {
    "gemini": "casefile.providers.gemini:create_chat",
    "fake": "casefile.providers.fake:create_chat",
}
_BUILTIN_EMBEDDING: dict[str, str] = {
    "ollama": "casefile.providers.ollama:create_embeddings",
    "fake": "casefile.providers.fake:create_embeddings",
}

_chat: dict[str, ChatFactory] = {}
_embedding: dict[str, EmbeddingFactory] = {}


class ProviderError(RuntimeError):
    """Unknown provider or provider misconfiguration."""


@dataclass(frozen=True)
class ChatModelInfo:
    provider: str
    model: str


def register_chat(name: str, factory: ChatFactory) -> None:
    _chat[name] = factory


def register_embedding(name: str, factory: EmbeddingFactory) -> None:
    _embedding[name] = factory


def _load(path: str) -> object:
    module, attr = path.split(":")
    return getattr(import_module(module), attr)


def _resolve_chat(name: str) -> ChatFactory:
    if name in _chat:
        return _chat[name]
    if name in _BUILTIN_CHAT:
        factory: ChatFactory = _load(_BUILTIN_CHAT[name])  # type: ignore[assignment]
        return factory
    known = sorted({*_chat, *_BUILTIN_CHAT})
    raise ProviderError(f"Unknown chat provider {name!r}. Known: {known}")


def _resolve_embedding(name: str) -> EmbeddingFactory:
    if name in _embedding:
        return _embedding[name]
    if name in _BUILTIN_EMBEDDING:
        factory: EmbeddingFactory = _load(_BUILTIN_EMBEDDING[name])  # type: ignore[assignment]
        return factory
    known = sorted({*_embedding, *_BUILTIN_EMBEDDING})
    raise ProviderError(f"Unknown embedding provider {name!r}. Known: {known}")


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    settings = settings or get_settings()
    return _resolve_chat(settings.chat_provider)(settings)


def get_embeddings(settings: Settings | None = None) -> Embeddings:
    settings = settings or get_settings()
    return _resolve_embedding(settings.embedding_provider)(settings)


def chat_model_info(settings: Settings | None = None) -> ChatModelInfo:
    """Provider + model identifiers, recorded with every LLM call and eval report."""
    settings = settings or get_settings()
    return ChatModelInfo(provider=settings.chat_provider, model=settings.chat_model)
