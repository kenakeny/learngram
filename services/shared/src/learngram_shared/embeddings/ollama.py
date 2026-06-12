from ..config import settings


class OllamaEmbeddings:
    def __init__(self) -> None:
        try:
            import httpx
        except ImportError as e:
            raise ImportError("Install httpx: uv add 'learngram-shared[ollama]'") from e
        self._httpx = httpx
        self._model = settings.ollama_embed_model
        self._base_url = settings.ollama_base_url

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            resp = self._httpx.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
                timeout=60,
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["embedding"])
        return embeddings
