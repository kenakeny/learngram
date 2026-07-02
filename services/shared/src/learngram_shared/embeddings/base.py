from typing import Literal, Protocol, runtime_checkable

# Retrieval-tuned models embed corpus text and search queries differently.
# Callers must say which side of the search they are embedding:
#   "document" — corpus text being indexed (chunks, node descriptions)
#   "query"    — search text used to find documents (RAG retrieval queries)
EmbedTask = Literal["document", "query"]


@runtime_checkable
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str], task: EmbedTask = "document") -> list[list[float]]:
        """Return a 768-dim embedding for each text in the input list."""
        ...
