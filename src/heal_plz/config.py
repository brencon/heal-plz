from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "heal-plz"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./heal_plz.db"

    # GitHub App
    GITHUB_APP_ID: int = 0
    GITHUB_APP_PRIVATE_KEY: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_OAUTH_CLIENT_ID: str = ""
    GITHUB_OAUTH_CLIENT_SECRET: str = ""

    # LLM Providers
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_AI_API_KEY: str = ""
    XAI_API_KEY: str = ""

    # Healing Engine
    PRIMARY_LLM_PROVIDER: str = "anthropic"
    PRIMARY_LLM_MODEL: str = "claude-sonnet-4-20250514"
    COUNCIL_CONFIDENCE_THRESHOLD: float = 0.8
    MAX_FIX_ATTEMPTS: int = 3
    AUTO_HEAL_BY_DEFAULT: bool = True

    # Background Processing
    MAX_CONCURRENT_TASKS: int = 5

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
