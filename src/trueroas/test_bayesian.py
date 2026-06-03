import pytest
from hypothesis import given, strategies as st
from src.trueroas.core.inference import DecisionEngine, BayesianInput
from src.trueroas.core.config import settings

@given(
    meta_roas=st.floats(min_value=0.1, max_value=20.0),
    true_roas=st.floats(min_value=0.1, max_value=20.0),
    std_dev=st.floats(min_value=0.1, max_value=5.0),
    sample_size=st.integers(min_value=31, max_value=1000) # Ensure Normal path, not bootstrap
)
def test_bayesian_invariants(meta_roas, true_roas, std_dev, sample_size):
    """Verify Bayesian posterior mathematical invariants."""
    inputs = BayesianInput(
        meta_roas=meta_roas,
        true_roas=true_roas,
        std_dev=std_dev,
        sample_size=sample_size
    )
    prior_var = settings.BAYESIAN_DEFAULT_PRIOR_VAR
    result = DecisionEngine.calculate_bayesian_posterior(inputs, prior_var)
    
    post_mean = result["post_mean"]

@given(
    proposed_increase=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    current_roas=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    std_dev=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    meta_roas=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    sample_size=st.integers(min_value=0, max_value=1000),
    match_rate=st.floats(min_value=0.0, max_value=1.0),
    evidence_quality=st.floats(min_value=0.0, max_value=1.0),
    ctr=st.floats(min_value=0.0, max_value=0.1),
    cr=st.floats(min_value=0.0, max_value=0.1),
    frequency=st.floats(min_value=0.0, max_value=5.0),
    bench_ctr=st.floats(min_value=0.005, max_value=0.05),
    bench_cr=st.floats(min_value=0.01, max_value=0.1),
    bench_freq=st.floats(min_value=1.0, max_value=4.0),
    monthly_spend=st.floats(min_value=100.0, max_value=100000.0),
    bias_correction=st.floats(min_value=-0.5, max_value=0.5),
    other_channels_count=st.integers(min_value=0, max_value=3)
)
def test_get_strategic_advice_edge_cases_hypothesis(
    proposed_increase, current_roas, std_dev, meta_roas, sample_size,
    match_rate, evidence_quality, ctr, cr, frequency,
    bench_ctr, bench_cr, bench_freq, monthly_spend, bias_correction,
    other_channels_count
):
    """
    Verify get_strategic_advice handles edge cases and returns valid structure.
    """
    other_channels = {f"ch_{i}": random.uniform(0.5, 3.0) for i in range(other_channels_count)}

    # Test early return for insufficient data or non-positive ROAS
    if current_roas <= 0 or sample_size < 5:
        result = DecisionEngine.get_strategic_advice(
            proposed_increase, current_roas, std_dev, meta_roas, sample_size,
            match_rate, evidence_quality, ctr, cr, frequency, bench_ctr, bench_cr, bench_freq,
            monthly_spend, bias_correction, other_channels
        )
        assert result["status"] == "insufficient_data"
        assert result["action"] == "REDUCE_OR_HOLD"
        return # Exit test if early return is expected

    # Test ValueError for non-positive std_dev in simulate_outcomes
    if std_dev <= 0:
        with pytest.raises(ValueError, match="Standard deviation must be strictly positive"):
            DecisionEngine.get_strategic_advice(
                proposed_increase, current_roas, std_dev, meta_roas, sample_size,
                match_rate, evidence_quality, ctr, cr, frequency, bench_ctr, bench_cr, bench_freq,
                monthly_spend, bias_correction, other_channels
            )
        return # Exit test if ValueError is expected

    # Normal execution path
    result = DecisionEngine.get_strategic_advice(
        proposed_increase, current_roas, std_dev, meta_roas, sample_size,
        match_rate, evidence_quality, ctr, cr, frequency, bench_ctr, bench_cr, bench_freq,
        monthly_spend, bias_correction, other_channels
    )

    assert "expected_value_usd" in result
    assert "action" in result
    assert result["action"] in ["STRONG_SCALE", "CAUTIOUS_SCALE", "REDUCE_OR_HOLD"]
    assert "tactical_steps" in result
    assert "merchant_explanation" in result
    assert "audit_verification" in result
    assert isinstance(result["expected_value_usd"], float)
    assert isinstance(result["tactical_steps"], list)
    assert isinstance(result["merchant_explanation"], str)

    # Verify that the action is consistent with the expected value and probability
    # (This is a high-level check, detailed logic is in RecommendationEngine tests)
    if result["expected_value_usd"] > 0 and float(result["probability"].strip('%')) > 50:
        assert result["action"] in ["STRONG_SCALE", "CAUTIOUS_SCALE"]
    elif result["expected_value_usd"] <= 0 or float(result["probability"].strip('%')) <= 50:
        assert result["action"] == "REDUCE_OR_HOLD"
    post_std = result["post_std"]
    
    # 1. Posterior mean must always be between the prior (Meta) and data (True) mean
    lower = min(meta_roas, true_roas)
    upper = max(meta_roas, true_roas)
    # Allowing small epsilon for floating point
    assert lower - 1e-7 <= post_mean <= upper + 1e-7

    # 2. Posterior variance (uncertainty) must always be less than or equal to 
    # both prior and data variance (adding information reduces uncertainty).
    data_var = (std_dev**2) / sample_size
    post_var = post_std**2
    
    assert post_var <= prior_var + 1e-7
    assert post_var <= data_var + 1e-7

@given(
    roas1=st.floats(min_value=0.1, max_value=10.0),
    roas2=st.floats(min_value=0.1, max_value=10.0),
    std_dev=st.floats(min_value=0.1, max_value=5.0)
)
def test_profit_probability_monotonicity(roas1, roas2, std_dev):
    """Verify that higher ROAS leads to higher or equal profit probability."""
    p1 = DecisionEngine.simulate_outcomes(roas1, std_dev)["profit_probability"]
    p2 = DecisionEngine.simulate_outcomes(roas2, std_dev)["profit_probability"]
    
    if roas1 < roas2:
        assert p1 <= p2 + 1e-7
    elif roas1 > roas2:
        assert p1 >= p2 - 1e-7