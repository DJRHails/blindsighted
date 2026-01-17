from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Agent settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google AI API (for Gemini)
    google_api_key: str = ""

    # API Backend URL
    api_base_url: str = "http://localhost:8000"

    # ElevenLabs Conversational AI (for reference)
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = "agent_0701kf5rm5s6f7jtnh7swk9nkx0a"


settings = Settings()
