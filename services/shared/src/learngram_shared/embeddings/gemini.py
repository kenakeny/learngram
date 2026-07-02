from ..config import settings
from .base import EmbedTask

_GEMINI_TASK = {"document": "RETRIEVAL_DOCUMENT", "query": "RETRIEVAL_QUERY"}


class GeminiEmbeddings:
    def __init__(self) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise ImportError("Install google-genai: uv add 'learngram-shared[gemini]'") from e
        if not settings.gemini_api_key:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=gemini but GEMINI_API_KEY is unset. "
                "Set the key in .env, or use EMBEDDING_PROVIDER=ollama."
            )
        self._types = types
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embed_model

    def embed(self, texts: list[str], task: EmbedTask = "document") -> list[list[float]]:
        result = self._client.models.embed_content(
            model=self._model,
            contents=texts,
            config=self._types.EmbedContentConfig(task_type=_GEMINI_TASK[task]),
        )
        return [e.values for e in result.embeddings]
