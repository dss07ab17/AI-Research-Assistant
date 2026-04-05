from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Research Assistant Agent"
    app_version: str = "0.1.0"
    data_dir: Path = Field(default=Path("data"))
    storage_dir: Path = Field(default=Path("data/storage"))
    download_dir: Path = Field(default=Path("data/downloads"))
    chunk_size: int = 900
    chunk_overlap: int = 150
    embedding_batch_size: int = 16
    max_papers: int = 5
    max_chunks: int = 6
    max_chunks_per_paper: int = 2
    lexical_boost_weight: float = 0.15
    request_timeout_seconds: int = 30
    user_agent: str = "ai-research-assistant/0.1.0"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_model: str = "gpt-4.1-mini"
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    return settings
