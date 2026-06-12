import json
from ..config import settings


class GeminiLLM:
    def __init__(self, model: str | None = None) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise ImportError("Install google-genai: uv add 'learngram-shared[gemini]'") from e

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = model or settings.gemini_gen_model
        self._types = types

    def generate(self, prompt: str, schema: dict | None = None) -> str | dict:
        if schema:
            config = self._types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            )
        else:
            config = None

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        text = response.text
        return json.loads(text) if schema else text
