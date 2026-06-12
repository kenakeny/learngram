from ..config import settings
from .base import EmbeddingProvider


def get_embeddings(provider: str | None = None) -> EmbeddingProvider:
    provider = provider or settings.embedding_provider
    if provider == "gemini":
        from .gemini import GeminiEmbeddings
        return GeminiEmbeddings()
    if provider == "ollama":
        from .ollama import OllamaEmbeddings
        return OllamaEmbeddings()
    raise ValueError(f"Unknown embedding provider: {provider!r}. Set EMBEDDING_PROVIDER=gemini or ollama.")
