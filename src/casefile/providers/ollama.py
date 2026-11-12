from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from casefile.config import Settings


def create_embeddings(settings: Settings) -> Embeddings:
    return OllamaEmbeddings(model=settings.embedding_model, base_url=settings.ollama_base_url)
