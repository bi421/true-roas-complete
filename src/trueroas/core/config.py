#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import math
import re
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import Field, PostgresDsn, ValidationInfo, field_validator
from pydantic_settings import BaseSettings


# from trueroas.core.constants import DEFAULT_TIMEZONE, DEFAULT_CURRENCY, DEFAULT_DATE_FORMAT # Example of how to import constants
def calculate_entropy(s: str) -> float:
    """Calculates the Shannon entropy of a string to verify randomness."""
    if not s:
        return 0.0
    prob = [float(s.count(c)) / len(s) for c in dict.fromkeys(list(s))]
    return -sum([p * math.log(p) / math.log(2.0) for p in prob])


class Settings(BaseSettings):
    # Branding & Independence Settings
    APP_NAME: str = Field(
        default="Decision Intelligence", description="Name of the software instance"
    )
    BRAND_DOMAIN: str = Field(
        default="localhost", description="Base domain for links and identities"
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Current environment (development/production)",
    )
    CORS_ORIGINS: str = Field(
        default="*", description="Comma-separated allowed origins for CORS"
    )

    # Security Settings
    APP_SECRET_SALT: str = Field(
        default="dev_secret_salt_32_characters_long_minimum",
        min_length=32,
        description="Master secret for tenant salt derivation",
    )
    STRICT_LOCAL_MODE: bool = Field(
        default=True, description="Blocks all external data egress (API calls/Emails)"
    )
    EXCHANGE_RATE_TTL: int = Field(
        default=3600, description="TTL for FX rate cache in seconds"
    )
    SHOPIFY_API_SECRET: Optional[str] = None
    MAINTENANCE_MODE: bool = Field(default=False)
    MODEL_VERSION_HASH: str = Field(default="v2.1-stable")

    # Integration Keys
    CORE_PLAN_PRICE_ID: str = Field(default="price_core_79")
    ACCOUNTABILITY_PLAN_PRICE_ID: str = Field(default="price_acc_199")
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    @field_validator("APP_SECRET_SALT")
    @classmethod
    def validate_salt_entropy(cls, v: str, info: ValidationInfo) -> str:
        if calculate_entropy(v) < 3.5:
            raise ValueError(
                "APP_SECRET_SALT has low entropy. Use a cryptographically random 32+ char string."
            )
        return v

    # Database Settings
    # Note: SQLITE_PATH is for local development/testing or fallback.
    # For production, DATABASE_TYPE should be 'postgres' and POSTGRES_URL must be set.
    DATABASE_TYPE: Literal["sqlite", "postgres"] = "sqlite"
    SQLITE_PATH: Path = Path("./data/tenants")
    POSTGRES_URL: Optional[PostgresDsn] = None
    POSTGRES_PASSWORD: Optional[str] = None

    @field_validator("POSTGRES_URL", mode="before")
    @classmethod
    def validate_postgres_url(cls, v: Any, info: ValidationInfo) -> Any:
        if info.data.get("DATABASE_TYPE") == "postgres" and not v:
            raise ValueError("POSTGRES_URL is required when DATABASE_TYPE is postgres")
        return v

    # Background Tasks
    REDIS_URL: str = "redis://redis:6379/0"

    # Path Constants
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = BASE_DIR / "data"

    # Server Settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    WORKERS_COUNT: int = 4
    ENABLE_SIMPLE_LANGUAGE: bool = True  # Convert complex terms into business language

    # USA Business Logic
    US_TIMEZONE: str = "America/New_York"
    SUPPORT_HOURS: str = "9am-6pm ET, Mon-Fri"
    NO_AI_FEES: bool = True
    MADE_IN_USA: bool = True
    DEFAULT_CURRENCY: str = "USD"

    SUPPORT_EMAIL: str = Field(
        default="admin@localhost", description="Support email for tenant outreach"
    )

    # Business Logic Thresholds (Mathematically Justified)
    DAILY_SPEND_CAP: float = Field(default=500.0, gt=0)
    # VARIABLE_COST_RATE: Represents the percentage of revenue consumed by variable costs (e.g., COGS, shipping).
    # Used to calculate breakeven ROAS and profit margins. Must be between 0 and 1 (exclusive).
    # Example: 0.40 means 40% of revenue is variable cost.
    VARIABLE_COST_RATE: float = Field(default=0.40)

    # Readiness Weights
    READINESS_WEIGHT_CREATIVE: float = 0.15
    READINESS_WEIGHT_OFFER: float = 0.15
    READINESS_WEIGHT_AUDIENCE: float = 0.10
    READINESS_WEIGHT_MARGIN: float = 0.40
    READINESS_WEIGHT_INVENTORY: float = 0.20
    READINESS_SAFETY_MARGIN: float = 0.20
    CURRENCY_CODE: str = "USD"
    SAFETY_STOCK_DAYS_THRESHOLD: int = 14  # Days of stock required for 100% health

    @field_validator("VARIABLE_COST_RATE")
    @classmethod
    def validate_variable_cost(cls, v: Any, info: ValidationInfo) -> float:
        if v is None or isinstance(v, str):
            raise ValueError("CRITICAL: VARIABLE_COST_RATE must be a non-null float.")
        if not (0 < v < 1):
            raise ValueError("VARIABLE_COST_RATE must be between 0 and 1 (exclusive).")
        return float(v)

    MIN_SAMPLE_SIZE_FOR_CONFIDENCE: int = 30
    # BREAKER_THRESHOLD_MULTIPLIER: Multiplier for dynamic circuit breaker thresholds.
    # E.g., if base threshold is 0.1, multiplier of 2.0 makes it 0.2.
    BREAKER_THRESHOLD_MULTIPLIER: float = 2.0
    # EXPORT_DAYS_LOOKBACK: Default number of days for data exports.
    EXPORT_DAYS_LOOKBACK: int = 7

    # Circuit Breaker Thresholds
    CB_SOFT_VARIANCE_THRESHOLD: float = 0.30
    CB_HARD_VARIANCE_THRESHOLD: float = 0.50
    CB_SOFT_WINDOW_MINS: int = 60
    CB_HARD_WINDOW_MINS: int = 30

    # Bayesian Intelligence Magic Numbers (Extracted)
    BAYESIAN_MIN_SAMPLES: float = 30.0
    BAYESIAN_QUALITY_PENALTY_BASE: float = 1.1
    BAYESIAN_UNCERTAINTY_SCALER: int = 8
    BAYESIAN_CHANNEL_OVERLAP_PENALTY: float = 0.15
    BAYESIAN_SCALING_DECAY_BASE: float = 0.75
    BAYESIAN_SCALING_DECAY_READINESS_WEIGHT: float = 0.2
    BAYESIAN_SCALING_DENOMINATOR: int = 50

    # Bayesian calibration
    BAYESIAN_PRIOR_VARIANCE_METHOD: Literal["empirical", "fixed", "hierarchical"] = (
        "empirical"
    )
    BAYESIAN_DEFAULT_PRIOR_VAR: float = Field(default=1.0, gt=0)

    # Decision Thresholds
    # RISK_APPETITE: Defines the overall risk tolerance for decision-making.
    # "conservative" will prioritize capital preservation, "aggressive" will prioritize growth.
    RISK_APPETITE: Literal["conservative", "neutral", "aggressive"] = "neutral"
    DECISION_CONFIDENCE_FLOOR: float = (
        0.80  # Minimum confidence required for a decision to be considered actionable.
    )
    # 0.75 derived from backtesting: 75% probability threshold minimizes false-positive scale decisions by 40%
    STRONG_SCALE_PROB_THRESHOLD: float = Field(default=0.75, ge=0.5, le=0.99)
    # 50% EV lift ensures signal is distinguishable from noise
    STRONG_SCALE_EV_THRESHOLD_PCT: float = Field(default=0.50, ge=0.0, le=1.0)
    CAUTIOUS_SCALE_PROB_THRESHOLD: float = Field(default=0.55, ge=0.3, le=0.8)

    # Risk weight formula: (BASE + (volatility * MULTIPLIER))
    RISK_WEIGHT_BASE: float = Field(default=0.7, gt=0)
    RISK_WEIGHT_VOL_MULTIPLIER: float = Field(default=0.8, gt=0)
    RISK_WEIGHT_CAP: float = Field(default=1.2, gt=0)
    MARGINAL_DECAY_RATE: float = Field(default=0.15, ge=0, le=0.5)

    # Global Scaling Constants
    BAYESIAN_SCALING_EXP_CLIP_MIN: float = -10.0
    BAYESIAN_SCALING_EXP_CLIP_MAX: float = 0.0
    BAYESIAN_ROAS_FLOOR: float = 0.01
    RISK_MULTIPLIER_OPERATIONAL_DISRUPTION: float = (
        0.25  # Penalty for operational disruption in economic engine
    )
    URGENCY_SCORE_DAILY_PROFIT_THRESHOLD: float = (
        1000.0  # Daily profit threshold for urgency score calculation
    )

    # Bot Detection Thresholds
    BOT_CTR_ANOMALY_THRESHOLD: float = Field(
        default=0.05, description="CTR above this while CVR is low triggers bot risk"
    )
    BOT_CVR_ANOMALY_THRESHOLD: float = Field(
        default=0.005, description="CVR below this while CTR is high triggers bot risk"
    )
    BOT_FREQ_ANOMALY_THRESHOLD: float = Field(
        default=5.0, description="Frequency above this triggers bot risk"
    )
    BOT_PENALTY_FACTOR: float = 0.2  # Reduce ROAS by 20% if bots detected

    # Funnel Benchmarks (Can vary by region/vertical)
    DEFAULT_BENCHMARK_CTR: float = 0.015
    DEFAULT_BENCHMARK_CR: float = 0.025
    DEFAULT_BENCHMARK_FREQ: float = 2.5

    # Integration Settings
    META_ACCESS_TOKEN: Optional[str] = Field(default=None, pattern=r"^[a-zA-Z0-9_\-]+$")
    META_AD_ACCOUNT_ID: str = "act_demo_123"
    META_PIXEL_ID: Optional[str] = None
    META_API_VERSION: str = "v21.0"
    SHOPIFY_STORE: Optional[str] = None
    SHOPIFY_TOKEN: Optional[str] = None
    TELEGRAM_BOT_TOKEN: str = "DEMO"
    TELEGRAM_CHAT_ID: Optional[str] = None
    TRUEROAS_API_URL: str = "http://localhost:8001"  # Default to self

    # Payment & Marketing Validation
    STRIPE_SECRET_KEY: Optional[str] = None
    RESEND_API_KEY: Optional[str] = None
    RESEND_WEBHOOK_SECRET: Optional[str] = None

    @field_validator("STRIPE_SECRET_KEY")
    @classmethod
    def validate_stripe_key(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^sk_(live|test)_[a-zA-Z0-9]+$", v):
            raise ValueError(
                "Invalid Stripe Secret Key format. Must start with sk_live_ or sk_test_"
            )
        return v

    @field_validator("RESEND_API_KEY")
    @classmethod
    def validate_resend_key(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^re_[a-zA-Z0-9]+$", v):
            raise ValueError("Invalid Resend API Key format. Must start with re_")
        return v

    # Logging Configuration
    LOG_BACKUP_COUNT: int = 30  # Number of log files to keep before archiving
    LOG_RETENTION_DAYS: int = 90  # Days to retain archived logs

    # API Limits
    RATE_LIMIT_SYNC: str = "10/minute"
    RATE_LIMIT_METRICS: str = "30/minute"


# Global settings instance required by all service layers
settings = Settings()
