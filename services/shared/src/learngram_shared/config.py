from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql://learngram:learngram@localhost:5432/learngram"

    # LLM
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_gen_model: str = "gemini-2.5-flash"
    gemini_flash_model: str = "gemini-2.5-flash"
    gemini_embed_model: str = "text-embedding-004"

    # Rate limiting (requests per minute against the LLM provider)
    llm_rpm: int = 10  # gemini-2.5-flash free tier = 10 RPM
    llm_max_retries: int = 5

    # Embeddings
    embedding_provider: str = "gemini"
    embedding_dim: int = 768

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_gen_model: str = "qwen2.5"
    ollama_embed_model: str = "nomic-embed-text"


settings = Settings()
