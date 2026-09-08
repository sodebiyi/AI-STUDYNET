"""
Application settings, loaded from environment variables.

Nothing secret is hardcoded here — see .env.example at the repo root for the
full list of variables a deployment must set.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Core ---
    APP_NAME: str = "NetMentor AI"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://netmentor:netmentor@localhost:5432/netmentor"

    # --- Auth / JWT ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # --- AI Coach ---
    # NetMentor's AI Network Coach ships with a rule-based Socratic-questioning
    # engine (app/services/coach.py) that needs no external API key. Setting
    # AI_COACH_PROVIDER=llm and supplying an API key lets a future build swap
    # in a real LLM behind the same CoachEngine interface without touching
    # any caller.
    AI_COACH_PROVIDER: str = "rule_based"  # "rule_based" | "llm"
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "claude-sonnet-4-5"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
