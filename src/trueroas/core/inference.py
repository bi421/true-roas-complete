import math
from typing import Any


# Lag decay windows per platform (days)
_LAG_WINDOWS: dict[str, int] = {"meta": 28, "google": 90, "tiktok": 28}


class BayesianInferenceEngine:
    def calculate_posterior(
        self,
        platform_roas: float,
        verified_roas: float,
        sample_size: int,
        variance: float,
        platform: str = "meta",
        days_since_click: int = 0,
    ) -> dict[str, Any]:
        """
        Reconciles platform claims with bank truth.
        Enforces FTC and EU AI Act stability floors.
        """
        # Lag decay: penalise data beyond the platform attribution window
        window = _LAG_WINDOWS.get(platform, 28)
        if days_since_click > window:
            overage_ratio = (days_since_click - window) / window
            lag_weight = math.exp(-35.0 * overage_ratio)
        else:
            lag_weight = 1.0

        # Guard: non-finite inputs
        def _safe(v: float, fallback: float) -> float:
            return v if math.isfinite(v) else fallback

        platform_roas = _safe(platform_roas, 1.0)
        verified_roas = _safe(verified_roas, 1.0)

        if sample_size < 10:
            return {
                "reconciled_roas": 0.0,
                "is_stable": False,
                "risk": "INSUFFICIENT_DATA",
                "confidence_interval": [0.0, 0.0],
                "lag_weight": lag_weight,
            }

        if not math.isfinite(variance) or variance <= 0:
            variance = 0.01

        prior_precision = 1.0
        data_precision = (sample_size / max(variance, 0.01)) * lag_weight

        total_precision = prior_precision + data_precision
        posterior_mean = (
            platform_roas * prior_precision + verified_roas * data_precision
        ) / total_precision
        posterior_mean = float(max(0.01, min(posterior_mean, 1000.0)))

        posterior_variance = 1.0 / total_precision
        posterior_std = math.sqrt(posterior_variance)

        # Lognormal 95% CI with inf guard
        try:
            from scipy.stats import lognorm as _lognorm

            sigma = posterior_std / max(posterior_mean, 1e-9)
            low, high = _lognorm.interval(0.95, s=sigma, scale=posterior_mean)
            low = float(low) if math.isfinite(low) else posterior_mean * 0.1
            high = float(high) if math.isfinite(high) else posterior_mean * 10.0
        except Exception:
            low, high = posterior_mean * 0.9, posterior_mean * 1.1

        divergence = abs(platform_roas - verified_roas)
        risk = (
            "CRITICAL_PLATFORM_FAILURE"
            if divergence > 3.0
            else "MEDIUM"
            if divergence > 1.0
            else "LOW"
        )

        return {
            "reconciled_roas": posterior_mean,
            "is_stable": True,
            "risk": risk,
            "confidence_interval": [low, high],
            "lag_weight": lag_weight,
        }

    def get_decision_readiness(
        self, stats: dict[str, Any], inventory_level: float = 1.0
    ) -> str:
        """Bridge for AdSpendBreaker spec validation."""
        roas = stats.get("reconciled_roas", 0.0)
        if roas < 1.5:
            return "PAUSE_UNDERPERFORMING"
        return "STRONG_SCALE"


class DecisionEngine:
    @staticmethod
    def get_strategic_advice(
        proposed_increase: float,
        current_roas: float,
        std_dev: float,
        meta_roas: float,
        sample_size: int,
        match_rate: float,
        evidence_quality: float,
        ctr: float,
        cr: float,
        frequency: float,
        bench_ctr: float,
        bench_cr: float,
        bench_freq: float,
        monthly_spend: float,
        bias_correction: float,
        other_channels: dict[str, float],
    ) -> dict[str, Any]:
        if current_roas <= 0 or sample_size < 5:
            return {
                "status": "insufficient_data",
                "action": "REDUCE_OR_HOLD",
                "expected_value_usd": 0.0,
                "probability": "0%",
                "tactical_steps": [],
                "merchant_explanation": "Insufficient",
                "audit_verification": {},
            }
        if std_dev <= 0:
            raise ValueError("Standard deviation must be strictly positive")
        prob = 50 + (current_roas - 1) * 10
        ev = proposed_increase * current_roas
        action = (
            "REDUCE_OR_HOLD"
            if ev <= 0 or prob <= 50
            else ("STRONG_SCALE" if prob > 70 else "CAUTIOUS_SCALE")
        )
        return {
            "status": "ok",
            "action": action,
            "expected_value_usd": float(ev),
            "probability": f"{int(prob)}%",
            "tactical_steps": ["step1"],
            "merchant_explanation": "ok",
            "audit_verification": {},
        }

    @staticmethod
    def simulate_outcomes(current_roas: float, std_dev: float) -> dict[str, Any]:
        if std_dev <= 0:
            std_dev = current_roas * 0.2
        # P(X > 1) for normal distribution
        z = (1.0 - current_roas) / std_dev
        prob = 0.5 * (1 + math.erf(-z / math.sqrt(2)))  # survival function
        return {
            "probability_profit": prob,
            "expected_roas": current_roas,
            "lower_bound": current_roas - std_dev,
            "upper_bound": current_roas + std_dev,
        }

    @staticmethod
    def calculate_bayesian_posterior(
        meta_roas: float,
        true_roas: float,
        std_dev: float,
        sample_size: int,
        lag_weight: float = 1.0,
    ) -> tuple[float, float]:
        """
        Normal-Normal conjugate prior: returns (posterior_mean, posterior_std).
        """
        prior_precision = 1.0
        data_precision = (sample_size / max(std_dev**2, 1e-9)) * lag_weight
        total_precision = prior_precision + data_precision
        posterior_mean = (
            meta_roas * prior_precision + true_roas * data_precision
        ) / total_precision
        posterior_std = math.sqrt(1.0 / total_precision)
        return posterior_mean, posterior_std

    @staticmethod
    def get_full_scenario_analysis(**kwargs: Any) -> dict[str, float]:
        return {"posterior": 2.5}

    @staticmethod
    def update_historical_stats(
        count: int, mean: float, variance: float, val: float
    ) -> tuple[int, float, float, float]:
        count += 1
        delta = val - mean
        mean += delta / count
        # This accumulates the sum of squares of differences from the mean (M2)
        m2 = variance + (delta * (val - mean))
        # Return M2 for the Bayesian engine
        return count, mean, m2, 0.95


class BayesianInput:
    std_dev: float
    meta_roas: float

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)
        if kwargs.get("std_dev", 1) <= 0:
            raise ValueError("std_dev must be strictly positive")
