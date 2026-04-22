from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "multimodal_rag"

    # Ollama
    ollama_host: str = "localhost:11434"
    ollama_text_model: str = "mistral:7b-instruct"
    ollama_vision_model: str = "llava:7b"

    # Embeddings
    embedding_model: str = "BAAI/bge-m3-small"
    embedding_deivce: str = "cpu"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 7860
    log_level: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
