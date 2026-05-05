from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_port: int = 8000

    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/compass"

    llm_provider: Literal["gemini", "ollama"] = "gemini"

    gemini_api_key: str = ""
    gemini_model_primary: str = "gemini-2.5-flash"
    gemini_model_fallback: str = "gemini-2.5-flash-lite"

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model_primary: str = "qwen2.5:14b"
    ollama_model_fallback: str = "qwen2.5:7b"

    gcp_project_id: str = ""
    gcp_region: str = "asia-east1"
    embedding_model: str = "text-embedding-005"
    google_application_credentials: str = ""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    tavily_api_key: str = ""
    jina_api_key: str = ""
    finmind_token: str = ""

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    reranker_url: str = "http://reranker:8001/rerank"

    rate_limit_per_minute: int = Field(default=20, ge=1)

    @property
    def is_dev(self) -> bool:
        return self.env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
