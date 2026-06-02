import pytest
from scipy import stats
from src.trueroas.core.inference import DecisionEngine

def test_simulate_outcomes_basic_precision():
    """
    Verify SciPy precision in standard cases.
    When ROAS = 2.0 and std_dev = 0.5:
    Z-score (for 1.0) = (1.0 - 2.0) / 0.5 = -2.0
    Normal SF(-2.0) ≈ 0.9772
    """
    current_roas = 2.0
    std_dev = 0.5
    
    res = DecisionEngine.simulate_outcomes(current_roas, std_dev)
    
    # Verify directly using SciPy
    expected_prob = stats.norm.sf(1.0, loc=current_roas, scale=std_dev)
    expected_p10 = stats.norm.ppf(0.1, loc=current_roas, scale=std_dev)
    expected_p90 = stats.norm.ppf(0.9, loc=current_roas, scale=std_dev)
    
    assert res["profit_probability"] == pytest.approx(expected_prob)
    assert res["expected_roas"] == 2.0
    assert res["volatility_index"] == 0.25 # 0.5 / 2.0
    # Check while accounting for rounding
    assert res["pessimistic_bound"] == pytest.approx(expected_p10, abs=0.01)
    assert res["optimistic_bound"] == pytest.approx(expected_p90, abs=0.01)

def test_simulate_outcomes_zero_std_dev_handling():
    """Verify 20% volatility usage when std_dev is 0 or negative."""
    current_roas = 3.0
    
    # When passing std_dev = 0
    res = DecisionEngine.simulate_outcomes(current_roas, 0)
    
    expected_std = 3.0 * 0.2 # 0.6
    assert res["volatility_index"] == 0.2
    
    expected_prob = stats.norm.sf(1.0, loc=current_roas, scale=expected_std)
    assert res["profit_probability"] == pytest.approx(expected_prob)

def test_simulate_outcomes_logical_consistency():
    """Verify logical order of bounds."""
    res = DecisionEngine.simulate_outcomes(1.5, 0.4)
    
    # 10% bound must be less than mean, 90% bound must be greater than mean
    assert res["pessimistic_bound"] < res["expected_roas"]
    assert res["optimistic_bound"] > res["expected_roas"]
    
    # Probability of profit must be > 50% when ROAS > 1.0
    if res["expected_roas"] > 1.0:
        assert res["profit_probability"] > 0.5

def test_simulate_outcomes_loss_scenario():
    """Verify low probability when in loss scenario (ROAS < 1.0)."""
    # ROAS 0.5, very low volatility 0.1
    res = DecisionEngine.simulate_outcomes(0.5, 0.1)
    
    # Profit probability should be nearly zero
    assert res["profit_probability"] < 0.01
    assert res["optimistic_bound"] < 1.0 # Should not reach 1.0 even in best case

def test_volatility_index_calculation():
    """Verify volatility index calculation."""
    res = DecisionEngine.simulate_outcomes(4.0, 1.0)
    assert res["volatility_index"] == 0.25 # 1.0 / 4.0
    
    res_high_vol = DecisionEngine.simulate_outcomes(4.0, 2.0)
    assert res_high_vol["volatility_index"] == 0.5 # 2.0 / 4.0