import json
import re
from ..config import settings


class OllamaLLM:
    def __init__(self, model: str | None = None) -> None:
        try:
            import httpx
        except ImportError as e:
            raise ImportError("Install httpx: uv add 'learngram-shared[ollama]'") from e
        self._httpx = httpx
        self._model    = model or settings.ollama_gen_model
        self._base_url = settings.ollama_base_url

    def generate(self, prompt: str, schema: dict | None = None) -> str | dict:
        # Explicit num_predict: some models ship Modelfiles with small caps and
        # a mid-JSON truncation turns into an unparseable response downstream.
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 2048},
        }
        if schema:
            # Ask for JSON output; full schema support varies by model
            payload["format"] = "json"

        resp = self._httpx.post(
            f"{self._base_url}/api/generate",
            json=payload,
            timeout=180,
        )
        resp.raise_for_status()
        text: str = resp.json()["response"]

        if schema:
            return self._parse_json(text)
        return text

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Parse JSON from model output, tolerating markdown fences and stray text."""
        text = text.strip()
        # Strip ```json ... ``` fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Find first { ... } block
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"No JSON found in model response:\n{text[:300]}")
