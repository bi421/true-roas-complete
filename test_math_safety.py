#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import math
import pytest
from hypothesis import given, strategies as st
from trueroas.core.inference import BayesianInferenceEngine
import numpy as np

engine = BayesianInferenceEngine()

@given(
    platform_roas=st.floats(allow_nan=True, allow_infinity=True),
    verified_roas=st.floats(allow_nan=True, allow_infinity=True),
    sample_size=st.integers(min_value=-1000, max_value=10000),
    variance=st.floats(allow_nan=True, allow_infinity=True),
    days_since_click=st.integers(min_value=-1, max_value=100)
)
def test_calculate_posterior_stability(platform_roas, verified_roas, sample_size, variance, days_since_click):
    """
    Ensures BayesianInferenceEngine.calculate_posterior is numerically stable.
    Handles extreme ranges, NaNs, and Infinities without crashing.
    """
    result = engine.calculate_posterior(
        platform_roas=platform_roas,
        verified_roas=verified_roas,
        sample_size=sample_size,
        variance=variance,
        days_since_click=days_since_click
    )
    
    # Assertions for numeric stability
    assert isinstance(result['reconciled_roas'], (float, int))
    assert math.isfinite(result['reconciled_roas'])
    
    low, high = result['confidence_interval']
    assert math.isfinite(low)
    assert math.isfinite(high)
    
    assert result['risk'] in ["LOW", "MEDIUM", "CRITICAL_PLATFORM_FAILURE", "INSUFFICIENT_DATA"]

def test_variance_inflation_luxury_goods():
    """P1: High-variance store (luxury goods) should result in a conservative posterior.
    
    Prevents overconfidence in business truth when the variance is extremely high 
    (e.g., mixing $1 and $10,000 orders).
    """
    # platform_roas=5.0, verified_roas=1.1, sample_size=100, variance=2.5M
    result = engine.calculate_posterior(
        platform_roas=5.0, 
        verified_roas=1.1, 
        sample_size=100, 
        variance=2500000.0
    )
    assert math.isfinite(result['reconciled_roas'])
    # The engine should lean toward the Prior (Platform) or remain conservative 
    # because the data variance is too high to trust the Verified ROAS entirely.
    assert result['reconciled_roas'] > 1.1

def test_lognorm_infinite_bounds_guard():
    """P2: Ensure infinite bounds from lognorm.interval are caught and capped.
    
    Scenarios with extreme divergence and low sample size (high sigma_post) 
    can cause lognorm.interval to return inf.
    """
    # platform_roas=0.01, verified_roas=100, sample_size=15, variance=0.01
    result = engine.calculate_posterior(0.01, 100.0, 15, 0.01)
    low, high = result['confidence_interval']
    assert math.isfinite(low)
    assert math.isfinite(high)

def test_extreme_lag_decay():
    """P1: Verifies weight reduction for data beyond platform windows (EU AI Act transparency)."""
    # Meta max window is 28 days. Data from day 30 should be penalized.
    result = engine.calculate_posterior(5.0, 4.0, 100, 1.0, platform='meta', days_since_click=30)
    assert result['lag_weight'] <= 0.1