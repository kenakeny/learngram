from ..config import settings


class GeminiEmbeddings:
    def __init__(self) -> None:
        try:
            from google import genai
        except ImportError as e:
            raise ImportError("Install google-genai: uv add 'learngram-shared[gemini]'") from e
        if not settings.gemini_api_key:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=gemini but GEMINI_API_KEY is unset. "
                "Set the key in .env, or use EMBEDDING_PROVIDER=ollama."
            )
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embed_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self._client.models.embed_content(model=self._model, contents=texts)
        return [e.values for e in result.embeddings]
