# Copyright (c) 2024-2026 TrueROAS Team.
# All rights reserved.

from pathlib import Path

from pydantic_settings import BaseSettings


class MarketSettings(BaseSettings):
    # Basic Settings
    app_name: str = "TrueROAS Decision Intelligence"
    currency_symbol: str = "$"
    support_email: str = "support@trueroas.com"

    # Financial Logic
    variable_cost_rate: float = 0.40  # Default 40% (Commission, Logistics, Returns)
    breakeven_roi: float = 1.67  # Formula: 1 / (1 - 0.40)

    # Industry Traffic Benchmarks
    benchmark_ctr: float = 0.015  # 1.5%
    benchmark_cvr: float = 0.025  # 2.5%
    benchmark_frequency: float = 3.0

    # Bot/Fraud Defense Parameters
    bot_ctr_threshold: float = 0.08  # CTR > 8% flagged as high risk
    fraud_cvr_alert_line: float = 0.25  # CVR > 25% suspected click-farming
    defense_deduction_factor: float = 0.80  # Penalty factor for suspicious data

    # Decision Thresholds
    scaling_probability_threshold: float = 0.75

    # Path Management
    root_dir: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = root_dir / "data"


Settings = MarketSettings()
