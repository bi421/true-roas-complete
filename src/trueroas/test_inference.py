import pytest
import math
import numpy as np
from src.trueroas.core.inference import DecisionEngine, BayesianInput
from src.trueroas.core.config import settings

def test_welfords_algorithm_consistency():
    """Verify Welford's algorithm maintains accurate running mean and variance."""
    data = [10.0, 12.0, 8.0, 15.0, 9.0]
    count, mean, variance, confidence = 0, 0.0, 0.0, 0.0
    
    for val in data:
        count, mean, variance, confidence = DecisionEngine.update_historical_stats(
            count, mean, variance, val
        )
    
    assert count == len(data)
    assert mean == pytest.approx(np.mean(data))
    assert variance == pytest.approx(np.var(data, ddof=1))

def test_bayesian_posterior_conjugate_known_values():
    """
    Verify Bayesian reconciliation with user provided statistical example:
    μ₀=2.5, σ₀=0.5, n=100, x̄=3.0, σ=0.8
    Formula: μₙ = (σ²μ₀ + nσ₀²x̄) / (σ² + nσ₀²)
    Numerator: (0.64 * 2.5) + (100 * 0.25 * 3.0) = 1.6 + 75 = 76.6
    Denominator: 0.64 + (100 * 0.25) = 25.64
    Result: 76.6 / 25.64 ≈ 2.9875
    """
    inputs = BayesianInput(
        prior_std=0.5,
        meta_roas=2.5,
        true_roas=3.0,
        std_dev=0.8,
        sample_size=100
    )
    result = DecisionEngine.calculate_bayesian_posterior(inputs)
    
    # Note: 2.88 from prompt likely assumes different precision/sample logic,
    # but we assert mathematical consistency with the prompt's provided formula.
    assert result["post_mean"] == pytest.approx(2.9875, abs=1e-3)
    assert "risk_adjusted_roas" in result
    assert result["risk_adjusted_roas"] < result["post_mean"]

def test_bayesian_bootstrap_fallback_consistency():
    """Verify bootstrap fallback yields stable results for small sample sizes."""
    raw_data = [1.5, 2.5, 2.0, 3.0, 1.0]
    inputs = BayesianInput(
        meta_roas=4.0,
        true_roas=2.0,
        std_dev=1.0,
        sample_size=len(raw_data),
        raw_data=raw_data
    )
    # Ensure n < 30 to trigger bootstrap
    result = DecisionEngine.calculate_bayesian_posterior(inputs, 1.0)
    
    assert "post_mean" in result
    assert "post_std" in result
    assert result["post_mean"] > 0

def test_invalid_bayesian_input():
    """Ensure ValueError is raised for non-positive standard deviation."""
    with pytest.raises(ValueError, match="std_dev must be strictly positive"):
        inputs = BayesianInput(meta_roas=4.0, true_roas=2.0, std_dev=0.0, sample_size=10)
        DecisionEngine.calculate_bayesian_posterior(inputs, 1.0)