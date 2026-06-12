from ..config import settings
from .base import LLMProvider


def get_llm(provider: str | None = None) -> LLMProvider:
    provider = provider or settings.llm_provider
    if provider == "gemini":
        from .gemini import GeminiLLM
        return GeminiLLM()
    if provider == "ollama":
        from .ollama import OllamaLLM
        return OllamaLLM()
    raise ValueError(f"Unknown LLM provider: {provider!r}. Set LLM_PROVIDER=gemini or ollama.")
