"""Helpers for passing embeddings to pgvector without the pgvector-python dep.

pgvector accepts a text literal like '[0.1,0.2,...]' cast to ::vector, so we
format Python float lists into that shape and let Postgres parse them.
"""


def to_pgvector(vec: list[float]) -> str:
    """Format an embedding as a pgvector text literal, e.g. '[0.1,0.2]'.

    Insert / query with a ``%s::vector`` placeholder.
    """
    return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"
