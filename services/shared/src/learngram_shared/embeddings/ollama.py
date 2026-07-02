from ..config import settings
from .base import EmbedTask

# nomic-embed-text is trained with task prefixes; embedding raw text without
# them collapses the distance range (we measured random chunk pairs at ~0.53
# cosine distance vs ~0.32 for true matches). Prefix every text accordingly.
_NOMIC_PREFIX = {"document": "search_document: ", "query": "search_query: "}


class OllamaEmbeddings:
    def __init__(self) -> None:
        try:
            import httpx
        except ImportError as e:
            raise ImportError("Install httpx: uv add 'learngram-shared[ollama]'") from e
        self._httpx = httpx
        self._model = settings.ollama_embed_model
        self._base_url = settings.ollama_base_url
        self._needs_prefix = "nomic" in self._model.lower()

    def embed(self, texts: list[str], task: EmbedTask = "document") -> list[list[float]]:
        if self._needs_prefix:
            prefix = _NOMIC_PREFIX[task]
            texts = [prefix + t for t in texts]

        # /api/embed accepts a batch; the older /api/embeddings was one call per text.
        resp = self._httpx.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model, "input": texts},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]
