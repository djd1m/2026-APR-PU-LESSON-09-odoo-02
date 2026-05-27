"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the FastAPI AI service.

    Provider switch: change AI_BASE_URL to point at Cloud.ru Foundation Models
    or OpenAI — both expose the same OpenAI-compatible chat completions API.
    """

    AI_BASE_URL: str  # e.g. "https://api.cloud.ru/v1" or "https://api.openai.com/v1"
    AI_API_KEY: str
    AI_MODEL: str = "qwen3-72b"

    REDIS_URL: str = "redis://redis:6379/0"
    DATABASE_URL: str
    ELASTICSEARCH_URL: str = "http://elasticsearch:9200"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore[call-arg]
