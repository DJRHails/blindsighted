from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # OpenRouter API
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Gemini Model
    gemini_model: str = "google/gemini-2.0-flash-exp:free"

    # CORS
    cors_origins: list[str] = ["http://localhost:8081", "exp://"]


settings = Settings()
