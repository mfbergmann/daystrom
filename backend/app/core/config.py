from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://daystrom:daystrom@localhost:5432/daystrom"
    redis_url: str = "redis://localhost:6379/0"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"
    ollama_embed_model: str = "nomic-embed-text"

    secret_key: str = "change-me-in-production"
    pin: str = ""  # Set to enable PIN auth; empty = no auth
    access_token_expire_minutes: int = 60 * 24 * 30  # 30 days

    embedding_dimensions: int = 768
    similarity_threshold: float = 0.7
    classification_confidence_high: float = 0.8
    classification_confidence_low: float = 0.5

    model_config = {"env_file": ".env"}


settings = Settings()
