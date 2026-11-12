from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from casefile.config import Settings
from casefile.providers.registry import ProviderError


def create_chat(settings: Settings) -> BaseChatModel:
    if settings.google_api_key is None:
        raise ProviderError("CHAT_PROVIDER=gemini requires GOOGLE_API_KEY")
    if not settings.chat_model:
        raise ProviderError("CHAT_PROVIDER=gemini requires CHAT_MODEL")
    return ChatGoogleGenerativeAI(
        model=settings.chat_model,
        api_key=settings.google_api_key,
        temperature=0.0,
    )
