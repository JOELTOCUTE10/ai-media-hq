"""Application settings. All values can be provided via environment variables / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # Core
    PROJECT_NAME: str = "AI Media HQ"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./ai_media_hq.db"
    SECRET_KEY: str = "change-me-generate-a-real-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Background task runner
    TASK_RUNNER_ENABLED: bool = True
    TASK_POLL_INTERVAL_SECONDS: float = 2.0
    # Agent initiative: idle agents propose work on this cadence.
    INITIATIVE_INTERVAL_SECONDS: float = 900.0  # 15 minutes
    # Cost guards: per-agent proposal caps per initiative pass/day.
    INITIATIVE_AGENTS_PER_PASS: int = 3
    INITIATIVE_MAX_PER_AGENT_PER_DAY: int = 3
    MAX_AGENT_RETRIES: int = 2

    # AI provider: openai | anthropic | fake (tests) | unconfigured
    AI_PROVIDER: str = "unconfigured"
    AI_MODEL: str = ""  # empty = provider default (see ai_providers.DEFAULT_MODELS)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    # Generic OpenAI-compatible endpoint (self-hosted or unlisted providers)
    OPENAI_BASE_URL: str = ""
    # Free-tier OpenAI-compatible providers (mnfst/awesome-free-llm-apis)
    GROQ_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Research integrations
    TAVILY_API_KEY: str = ""
    # Video generation
    VIDEO_PROVIDER_API_KEY: str = ""
    VIDEO_PROVIDER_URL: str = ""
    YOUTUBE_DATA_API_KEY: str = ""

    # YouTube publishing (Phase 6)
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = ""

    # Cost control
    MONTHLY_BUDGET_USD: float = 100.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
