from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Security Settings
    APP_SECRET_SALT: str = "change-me-to-something-secure"

    # Server Settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    SUPPORT_EMAIL: str = "support@trueroas.com"
    TRUEROAS_API_URL: str = "http://localhost:8001/api/v1/status"

    # Business Logic
    DAILY_SPEND_CAP: float = 500.0
    BREAKER_THRESHOLD_MULTIPLIER: float = 2.0
    EXPORT_DAYS_LOOKBACK: int = 7

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

settings = Settings()