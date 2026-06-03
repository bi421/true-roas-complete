#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import math
import pytest
from hypothesis import given, strategies as st, assume
from pydantic import ValidationError

from src.trueroas.core.inference import (
    DecisionEngine, 
    ROASInput, 
    BayesianInput, 
    DecisionInput, 
    BottleneckInput,
    HistoricalStatsInput,
    DomainError
)

# --- HYPOTHESIS PROPERTY-BASED TESTS ---

@given(
    current_roas=st.floats(min_value=-1e6, max_value=1e6, allow_nan=True, allow_infinity=True),
    std_dev=st.floats(min_value=-1e6, max_value=1e6, allow_nan=True, allow_infinity=True),
    sample_size=st.integers(min_value=-1000, max_value=1000)
)
def test_simulate_outcomes_math_safety(current_roas, std_dev, sample_size):
    """Mathematically proves simulate_outcomes is free of ZeroDivisionError and NaN leakage."""
    try:
        roas_in = ROASInput(current_roas=current_roas, std_dev=std_dev, sample_size=sample_size)
        res = DecisionEngine.simulate_outcomes(roas_in)
        
        # Assertions for numeric stability
        for key in ["profit_probability", "expected_roas", "volatility_index", "pessimistic_bound", "optimistic_bound"]:
            assert math.isfinite(res[key]), f"Non-finite value '{res[key]}' found in key '{key}'"
            
    except (ValidationError, ValueError, DomainError) as e:
        # Verify that error messages for invalid inputs are descriptive
        err_msg = str(e).lower()
        if current_roas < 0:
            assert any(x in err_msg for x in ["negative", "loss-making", "current_roas"])
        if std_dev <= 0:
            assert any(x in err_msg for x in ["greater than 0", "std_dev"])
    except ZeroDivisionError:
        pytest.fail("ZeroDivisionError reached within DecisionEngine.simulate_outcomes")

@given(
    current_count=st.integers(min_value=-1000, max_value=1000),
    current_mean=st.floats(min_value=-1e6, max_value=1e6, allow_nan=True, allow_infinity=True),
    current_variance=st.floats(min_value=-1e6, max_value=1e6, allow_nan=True, allow_infinity=True),
    new_value=st.floats(min_value=-1e6, max_value=1e6, allow_nan=True, allow_infinity=True)
)
def test_update_historical_stats_math_safety(current_count, current_mean, current_variance, new_value):
    """Verifies Welford's algorithm implementation stability."""
    try:
        stats_in = HistoricalStatsInput(
            current_count=current_count, 
            current_mean=current_mean, 
            current_variance=current_variance, 
            new_value=new_value
        )
        count, mean, var, conf = DecisionEngine.update_historical_stats(stats_in)
        
        assert math.isfinite(mean)
        assert math.isfinite(var)
        assert math.isfinite(conf)
        assert var >= 0
        
    except (ValidationError, ValueError) as e:
        pass
    except ZeroDivisionError:
        pytest.fail("ZeroDivisionError reached within DecisionEngine.update_historical_stats")

@given(
    meta_roas=st.floats(min_value=-1e6, max_value=1e6, allow_nan=True, allow_infinity=True),
    true_roas=st.floats(min_value=-1e6, max_value=1e6, allow_nan=True, allow_infinity=True),
    std_dev=st.floats(min_value=-1e6, max_value=1e6, allow_nan=True, allow_infinity=True),
    sample_size=st.integers(min_value=-1000, max_value=1000)
)
def test_calculate_bayesian_posterior_math_safety(meta_roas, true_roas, std_dev, sample_size):
    """Verifies Bayesian Precision weighting stability."""
    try:
        bayesian_in = BayesianInput(
            meta_roas=meta_roas, 
            true_roas=true_roas, 
            std_dev=std_dev, 
            sample_size=sample_size
        )
        res = DecisionEngine.calculate_bayesian_posterior(bayesian_in)
        
        assert math.isfinite(res["post_mean"])
        assert math.isfinite(res["post_std"])
        assert res["post_std"] >= 0
        
    except (ValidationError, ValueError) as e:
        pass
    except ZeroDivisionError:
        pytest.fail("ZeroDivisionError reached within DecisionEngine.calculate_bayesian_posterior")

# --- BOUNDARY VALUE TESTS ---

@pytest.mark.parametrize("roas, std, n, inc", [
    (0.0, 0.0, 0, 0.0),             # Exact Zeros
    (float('inf'), 1.0, 10, 1.0),   # Infinities
    (float('nan'), 1.0, 10, 1.0),   # NaNs
    (1e-308, 1e-308, 2, 1e-308),    # Near-zero (Denormals)
    (-1e-308, -1e-308, -1, -1e-308) # Negative Near-zero
])
def test_engine_boundaries_rejection(roas, std, n, inc):
    """Ensures problematic boundary values are rejected by the validation layer, not the math engine."""
    # We expect either ValidationError (Pydantic) or ValueError/DomainError (Engine Logic)
    with pytest.raises((ValidationError, ValueError, DomainError)):
        # Test Decision Input
        DecisionInput(
            proposed_increase=inc, 
            meta_roas=roas, 
            current_roas=roas, 
            std_dev=std, 
            sample_size=n
        )

# --- PARAMETERIZED PYTEST SCENARIOS ---

def test_calculate_bayesian_posterior_valid_scenarios():
    """Tests 10 valid scenarios to ensure high-precision results are finite."""
    scenarios = [
        {"meta": 4.0, "true": 2.0, "std": 1.0, "n": 10},
        {"meta": 2.5, "true": 3.0, "std": 0.5, "n": 100},
        {"meta": 10.0, "true": 1.0, "std": 5.0, "n": 5},
        {"meta": 1.1, "true": 1.2, "std": 0.1, "n": 30},
        {"meta": 0.5, "true": 0.5, "std": 0.2, "n": 15},
        {"meta": 100.0, "true": 90.0, "std": 10.0, "n": 200},
        {"meta": 1.0, "true": 10.0, "std": 2.0, "n": 7},
        {"meta": 5.0, "true": 5.0, "std": 0.01, "n": 1000},
        {"meta": 3.2, "true": 2.8, "std": 0.9, "n": 45},
        {"meta": 4.5, "true": 3.1, "std": 1.2, "n": 12},
    ]
    
    for s in scenarios:
        inp = BayesianInput(meta_roas=s["meta"], true_roas=s["true"], std_dev=s["std"], sample_size=s["n"])
        res = DecisionEngine.calculate_bayesian_posterior(inp)
        assert math.isfinite(res["post_mean"])
        assert math.isfinite(res["post_std"])

@pytest.mark.parametrize("std, n, expected_error", [
    (0.0, 10, "greater than 0"),
    (1.0, 0, "greater than or equal to 2"),
    (-1.0, 5, "greater than 0"),
])
def test_calculate_bayesian_posterior_invalid(std, n, expected_error):
    """Verifies specific rejection criteria for Bayesian input."""
    with pytest.raises(ValidationError) as exc:
        BayesianInput(meta_roas=4.0, true_roas=2.0, std_dev=std, sample_size=n)
    assert expected_error in str(exc.value)

def test_simulate_outcomes_zero_roas():
    """Proves that zero ROAS is caught as a ValueError by validators, preventing volatility div-by-zero."""
    with pytest.raises(ValueError, match="current_roas must be greater than 0"):
        ROASInput(current_roas=0.0, std_dev=0.5, sample_size=10)

def test_get_strategic_advice_zero_increase():
    """Verifies that zero proposed increase is rejected with a clear message."""
    with pytest.raises(ValidationError) as exc:
        DecisionInput(
            proposed_increase=0.0, 
            meta_roas=4.0, 
            current_roas=2.0, 
            std_dev=0.5, 
            sample_size=10
        )
    assert "greater than 0" in str(exc.value)

def test_get_strategic_advice_negative_roas():
    """Verifies that negative ROAS triggers a DomainError, not a mathematical failure."""
    with pytest.raises(DomainError, match="Negative ROAS indicates a loss-making campaign"):
        ROASInput(current_roas=-1.5, std_dev=0.5, sample_size=10)

def test_bottleneck_input_impossible_values():
    """Verifies that impossible CTR/CR values (> 1.0) are rejected."""
    with pytest.raises(ValidationError) as exc:
        BottleneckInput(ctr=1.1, cr=0.05, frequency=1.5)
    assert "less than or equal to 1" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        BottleneckInput(ctr=0.02, cr=2.5, frequency=1.5)
    assert "less than or equal to 1" in str(exc.value)