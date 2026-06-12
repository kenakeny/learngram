from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    def generate(self, prompt: str, schema: dict | None = None) -> str | dict:
        """Generate text or structured output from a prompt."""
        ...
