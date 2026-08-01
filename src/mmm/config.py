"""Application settings loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application configuration. Values come from env vars or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM provider ---
    llm_provider: str = "ollama"  # ollama | anthropic | openai
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- Model storage ---
    model_storage_backend: str = "local"  # local | s3 | r2
    model_storage_path: str = "./model_artifacts"

    # --- Queue ---
    redis_url: str = "redis://localhost:6379/0"

    # --- App ---
    env: str = "development"
    secret_key: str = "change-me"
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
