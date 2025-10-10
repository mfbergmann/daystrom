"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/daystrom"
    database_sync_url: str = "postgresql://user:password@localhost:5432/daystrom"
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Telegram Bot Configuration
    telegram_bot_token: str
    telegram_webhook_url: Optional[str] = None
    
    # Google Calendar Configuration
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    
    # Apple Calendar (CalDAV) Configuration
    caldav_url: Optional[str] = "https://caldav.icloud.com"
    caldav_username: Optional[str] = None
    caldav_password: Optional[str] = None
    
    # Application Settings
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    secret_key: str = "change-me-in-production"
    
    # Scheduling
    digest_time_daily: str = "08:00"
    digest_time_weekly: str = "09:00"
    timezone: str = "UTC"
    
    # OpenAI Model Configuration
    openai_model: str = "gpt-4o"
    openai_reasoning_model: str = "o1-preview"
    openai_embedding_model: str = "text-embedding-3-large"
    
    # Search Configuration
    max_search_results: int = 10
    similarity_threshold: float = 0.7


settings = Settings()

