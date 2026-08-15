from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Enterprise Document Q&A"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8000

    llm_provider: str = "ollama"
    embedding_provider: str = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "gemma2:2b"
    ollama_embedding_model: str = "nomic-embed-text"

    claude_api_key: str | None = None
    claude_model: str = "claude-sonnet-4-20250514"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    azure_openai_endpoint: str | None = None

    chroma_persist_dir: str = "./data/chroma_db"

    upload_dir: str = "./data/uploads"
    max_upload_size_mb: int = 50

    chunk_size: int = 2048
    chunk_overlap: int = 256

    default_top_k: int = 5
    default_temperature: float = 0.1
    default_collection: str = "default"

    prompts_dir: str = "./config/prompts"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "RAG_",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_prompt(filename: str) -> str:
    settings = get_settings()
    path = Path(settings.prompts_dir) / filename
    return path.read_text(encoding="utf-8")
