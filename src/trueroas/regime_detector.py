#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import math
from typing import List
import statistics


class RegimeDetector:
    """
    Detects market volatility (CPM spikes) and seasonality to trigger regime shifts.
    """

    @staticmethod
    def detect_volatility_shift(
        cpm_series: List[float], sensitivity: float = 2.0
    ) -> bool:
        """
        Returns True if the latest CPM is > sensitivity standard deviations from the mean.
        """
        if len(cpm_series) < 7:
            return False

        mean_cpm = statistics.mean(cpm_series[:-1])
        std_cpm = statistics.stdev(cpm_series[:-1])
        latest_cpm = cpm_series[-1]

        threshold = mean_cpm + (sensitivity * std_cpm)
        return latest_cpm > threshold

    @staticmethod
    def calculate_lag_weight(overage_ratio: float) -> float:
        """
        Lag decay formula per changelog 1.4.0:
        lag_weight = exp(-35 * overage_ratio)
        """
        return math.exp(-35 * overage_ratio)

    @staticmethod
    def detect_cpm_regime(spend_history: List[float]) -> int:
        """
        Detects CPM regime shifts using spend variance.
        If recent 14d spend variance > 2σ, relax patience_days from 3 to 5.
        """
        if len(spend_history) < 30:
            return 3

        # Baseline is everything up to the last 14 days
        baseline = spend_history[:-14]
        recent = spend_history[-14:]

        mu = statistics.mean(baseline)
        sigma = statistics.stdev(baseline)

        recent_mu = statistics.mean(recent)

        # If recent spend mean deviates by more than 2 sigma, we are in a high-volatility regime
        if abs(recent_mu - mu) > 2 * sigma:
            return 5

        return 3
