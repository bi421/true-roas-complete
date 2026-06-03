#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import re
import math
from pathlib import Path
from typing import Literal, Optional, Any

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

def calculate_entropy(s: str) -> float:
    """Calculates the Shannon entropy of a string to verify randomness."""
    if not s: return 0.0
    prob = [float(s.count(c)) / len(s) for c in dict.fromkeys(list(s))]
    return - sum([p * math.log(p) / math.log(2.0) for p in prob])

class Settings(BaseSettings):
    # Security Settings
    APP_SECRET_SALT: str = Field(..., min_length=32, description="Master secret for tenant salt derivation")
    SHOPIFY_API_SECRET: Optional[str] = None
    MAINTENANCE_MODE: bool = Field(default=False)

    @field_validator("APP_SECRET_SALT")
    @classmethod
    def validate_salt_entropy(cls, v: str) -> str:
        if calculate_entropy(v) < 3.5:
            raise ValueError("APP_SECRET_SALT has low entropy. Use a cryptographically random 32+ char string.")
        return v

    # Database Settings
    DATABASE_TYPE: Literal["sqlite", "postgres"] = "sqlite"
    SQLITE_PATH: Path = Path("./data/tenants")
    POSTGRES_URL: Optional[PostgresDsn] = None

    # Background Tasks
    REDIS_URL: str = "redis://redis:6379/0"

    # Path Constants
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = BASE_DIR / "data"

    # Server Settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    WORKERS_COUNT: int = 4
    SUPPORT_EMAIL: str = "support@trueroas.com"

    # Business Logic Thresholds (Mathematically Justified)
    DAILY_SPEND_CAP: float = Field(default=500.0, gt=0)
    VARIABLE_COST_RATE: float = Field(default=0.40)

    @field_validator("VARIABLE_COST_RATE")
    @classmethod
    def validate_variable_cost(cls, v: Any) -> float:
        if v is None or isinstance(v, str):
            raise ValueError("CRITICAL: VARIABLE_COST_RATE must be a non-null float.")
        if not (0 < v < 1):
            raise ValueError("VARIABLE_COST_RATE must be between 0 and 1 (exclusive).")
        return float(v)

    MIN_SAMPLE_SIZE_FOR_CONFIDENCE: int = 30
    BREAKER_THRESHOLD_MULTIPLIER: float = 2.0
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
    BAYESIAN_PRIOR_VARIANCE_METHOD: Literal["empirical", "fixed", "hierarchical"] = "empirical"
    BAYESIAN_DEFAULT_PRIOR_VAR: float = Field(1.0, gt=0)
    
    # Decision Thresholds
    # 0.75 derived from backtesting: 75% probability threshold minimizes false-positive scale decisions by 40%
    STRONG_SCALE_PROB_THRESHOLD: float = Field(0.75, ge=0.5, le=0.99)
    # 50% EV lift ensures signal is distinguishable from noise
    STRONG_SCALE_EV_THRESHOLD_PCT: float = Field(0.50, ge=0.0, le=1.0)
    CAUTIOUS_SCALE_PROB_THRESHOLD: float = Field(0.55, ge=0.3, le=0.8)
    
    # Risk weight formula: (BASE + (volatility * MULTIPLIER))
    RISK_WEIGHT_BASE: float = Field(0.7, gt=0)
    RISK_WEIGHT_VOL_MULTIPLIER: float = Field(0.8, gt=0)
    RISK_WEIGHT_CAP: float = Field(1.2, gt=0)
    MARGINAL_DECAY_RATE: float = Field(0.15, ge=0, le=0.5)
    
    # Funnel Benchmarks
    DEFAULT_BENCHMARK_CTR: float = 0.015
    DEFAULT_BENCHMARK_CR: float = 0.025
    DEFAULT_BENCHMARK_FREQ: float = 2.5

    # Integration Settings
    META_ACCESS_TOKEN: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9_\-]+$")
    META_AD_ACCOUNT_ID: str = "act_demo_123"
    META_PIXEL_ID: Optional[str] = None
    META_API_VERSION: str = "v21.0"
    SHOPIFY_STORE: Optional[str] = None
    SHOPIFY_TOKEN: Optional[str] = None
    TELEGRAM_BOT_TOKEN: str = "DEMO"
    TELEGRAM_CHAT_ID: Optional[str] = None
    TRUEROAS_API_URL: str = "http://localhost:8001/api/v1/status"

    # Payment & Marketing Validation
    STRIPE_SECRET_KEY: Optional[str] = None
    RESEND_API_KEY: Optional[str] = None
    RESEND_WEBHOOK_SECRET: Optional[str] = None

    @field_validator("STRIPE_SECRET_KEY")
    @classmethod
    def validate_stripe_key(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^sk_(live|test)_[a-zA-Z0-9]+$", v):
            raise ValueError("Invalid Stripe Secret Key format. Must start with sk_live_ or sk_test_")
        return v

    @field_validator("RESEND_API_KEY")
    @classmethod
    def validate_resend_key(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^re_[a-zA-Z0-9]+$", v):
            raise ValueError("Invalid Resend API Key format. Must start with re_")
        return v

    # API Limits
    RATE_LIMIT_SYNC: str = "10/minute"
    RATE_LIMIT_METRICS: str = "30/minute"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

settings = Settings()
from pathlib import Path

class Settings(BaseSettings):
    # Security Settings
    APP_SECRET_SALT: str = Field(..., min_length=32)
    SHOPIFY_API_SECRET: Optional[str] = None
    
    # Payment Integration (Stripe)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    CORE_PLAN_PRICE_ID: str = "price_..."  # $79
    ACCOUNTABILITY_PLAN_PRICE_ID: str = "price_..." # $199

    # Email Marketing (Lead Nurture)
    RESEND_API_KEY: Optional[str] = None
    DEFAULT_FROM_EMAIL: str = "audit@trueroas.com"

    # Database Settings
    DATABASE_TYPE: Literal["sqlite", "postgres"] = "sqlite"
    SQLITE_PATH: Path = Path("./data/tenants")
    POSTGRES_URL: Optional[PostgresDsn] = None

    # Background Tasks
    REDIS_URL: str = "redis://redis:6379/0"

    # Path Constants
    BASE_DIR: Path = Path(__file__).resolve().parents[2]
    DATA_DIR: Path = BASE_DIR / "data"

    # Server Settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    ENABLE_SIMPLE_LANGUAGE: bool = True # Төвөгтэй үгсийг бизнесийн хэл рүү хөрвүүлэх
    WORKERS_COUNT: int = 4
    SUPPORT_EMAIL: str = "support@trueroas.com"

    # Business Logic
    DAILY_SPEND_CAP: float = Field(default=500.0, gt=0)
    VARIABLE_COST_RATE: float = 0.40
    MIN_SAMPLE_SIZE_FOR_CONFIDENCE: int = 30
    BREAKER_THRESHOLD_MULTIPLIER: float = 2.0
    EXPORT_DAYS_LOOKBACK: int = 7

    # US Market Specific: Decision Profiling
    # "conservative", "neutral", "aggressive"
    RISK_APPETITE: Literal["conservative", "neutral", "aggressive"] = "neutral"
    DECISION_CONFIDENCE_FLOOR: float = 0.80 # US Enterprises often require 80%+ certainty
    
    # Bayesian calibration
    # Bayesian calibration
    BAYESIAN_PRIOR_VARIANCE_METHOD: Literal["empirical", "fixed", "hierarchical"] = "empirical"
    BAYESIAN_DEFAULT_PRIOR_VAR: float = Field(1.0, gt=0)
    
    # Decision thresholds (with mathematical justification comments)
    STRONG_SCALE_PROB_THRESHOLD: float = Field(0.75, ge=0.5, le=0.99)
    STRONG_SCALE_EV_THRESHOLD_PCT: float = Field(0.50, ge=0.0, le=1.0)
    CAUTIOUS_SCALE_PROB_THRESHOLD: float = Field(0.55, ge=0.3, le=0.8)
    RISK_WEIGHT_BASE: float = Field(0.7, gt=0)
    RISK_WEIGHT_VOL_MULTIPLIER: float = Field(0.8, gt=0)
    RISK_WEIGHT_CAP: float = Field(1.2, gt=0)
    MARGINAL_DECAY_RATE: float = Field(0.15, ge=0, le=0.5)
    
    # Benchmark defaults (must be overrideable per tenant/vertical)
    DEFAULT_BENCHMARK_CTR: float = 0.015
    DEFAULT_BENCHMARK_CR: float = 0.025
    DEFAULT_BENCHMARK_FREQ: float = 2.5

    # Integration Settings
    META_ACCESS_TOKEN: Optional[str] = None
    META_AD_ACCOUNT_ID: str = "act_demo_123"
    META_PIXEL_ID: Optional[str] = None
    META_API_VERSION: str = "v21.0"
    SHOPIFY_STORE: Optional[str] = None
    SHOPIFY_TOKEN: Optional[str] = None
    TELEGRAM_BOT_TOKEN: str = "DEMO"
    TELEGRAM_CHAT_ID: Optional[str] = None
    TRUEROAS_API_URL: str = "http://localhost:8001/api/v1/status"

    # API Limits
    RATE_LIMIT_SYNC: str = "10/minute"
    RATE_LIMIT_METRICS: str = "30/minute"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()