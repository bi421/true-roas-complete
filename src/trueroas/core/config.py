from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Path Constants
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = BASE_DIR / "data"

    # Security Settings
    APP_SECRET_SALT: str = "change-me-to-something-secure"

    # Server Settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    SUPPORT_EMAIL: str = "support@trueroas.com"
    TRUEROAS_API_URL: str = "http://localhost:8001/api/v1/status"

    # Business Logic
    DAILY_SPEND_CAP: float = Field(default=500.0, gt=0)
    BREAKER_THRESHOLD_MULTIPLIER: float = 2.0
    VARIABLE_COST_RATE: float = 0.40
    EXPORT_DAYS_LOOKBACK: int = 7
    MIN_SAMPLE_SIZE_FOR_CONFIDENCE: int = 30
    MARGINAL_DECAY_RATE: float = 0.15
    BAYESIAN_PRIOR_VARIANCE: float = 1.0 # How much we trust Meta's initial claim
    SIMULATION_DEFAULT_VOLATILITY: float = 0.2 # Default CV for zero std_dev
    ERROR_COST_LOSS_FACTOR: float = 0.8 # % of incremental spend lost if decision fails
    RISK_MULTIPLIER_OPERATIONAL_DISRUPTION: float = 1.25 # Penalty for indirect costs of failure
    URGENCY_SCORE_DAILY_PROFIT_THRESHOLD: float = 100.0 # Daily profit threshold for max urgency score

    # Logging and Maintenance
    LOG_BACKUP_COUNT: int = 30
    LOG_RETENTION_DAYS: int = 90

    # Integration Settings
    META_ACCESS_TOKEN: Optional[str] = None
    META_AD_ACCOUNT_ID: str = "act_demo_123"
    META_PIXEL_ID: Optional[str] = None
    META_API_VERSION: str = "v21.0"
    
    SHOPIFY_TOKEN: Optional[str] = None
    SHOPIFY_STORE_URL: Optional[str] = None
    SHOPIFY_ACCESS_TOKEN: Optional[str] = None
    
    TELEGRAM_BOT_TOKEN: str = "DEMO"

    @field_validator("APP_SECRET_SALT")
    @classmethod
    def salt_must_be_secure(cls, v: str) -> str:
        if v == "change-me-to-something-secure":
            raise ValueError("APP_SECRET_SALT is still using the default value. This is a critical security risk.")
        if len(v) < 16:
            raise ValueError("APP_SECRET_SALT must be at least 16 characters long.")
        return v

    @property
    def is_live(self) -> bool:
        """Returns True only if both Meta and Shopify tokens are provided."""
        return bool(self.META_ACCESS_TOKEN and self.SHOPIFY_TOKEN)

settings = Settings()