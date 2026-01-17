from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+psycopg://localhost/blindsighted"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Normalize DATABASE_URL to use +psycopg dialect if not specified"""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    # LiveKit
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_url: str = "ws://localhost:7880"

    # OpenRouter API
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Gemini Model (via OpenRouter)
    gemini_model: str = "google/gemini-2.0-flash-exp:free"

    # Google AI API (for direct Gemini calls)
    google_api_key: str = ""

    # ElevenLabs API
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

    # Cloudflare R2 Storage
    cloudflare_account_id: str = "78a27224f8a5e611fbb1a5999e2a77eb"
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "blindsighted"
    r2_public_url: str = "https://cdn.blindsighted.hails.info"

    # CORS
    cors_origins: str = "http://localhost:8081,exp://"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
