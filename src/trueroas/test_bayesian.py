import pytest
from hypothesis import given, strategies as st
from src.trueroas.core.inference import DecisionEngine
import random

@given(
    proposed_increase=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    current_roas=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    std_dev=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
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
    other_channels = {f"ch_{i}": random.uniform(0.5, 3.0) for i in range(other_channels_count)}

    if current_roas <= 0 or sample_size < 5:
        result = DecisionEngine.get_strategic_advice(
            proposed_increase, current_roas, std_dev, meta_roas, sample_size,
            match_rate, evidence_quality, ctr, cr, frequency, bench_ctr, bench_cr, bench_freq,
            monthly_spend, bias_correction, other_channels
        )
        assert result["status"] == "insufficient_data" or result["action"] == "REDUCE_OR_HOLD"
        return

    if std_dev <= 0:
        with pytest.raises(ValueError):
            DecisionEngine.get_strategic_advice(
                proposed_increase, current_roas, std_dev, meta_roas, sample_size,
                match_rate, evidence_quality, ctr, cr, frequency, bench_ctr, bench_cr, bench_freq,
                monthly_spend, bias_correction, other_channels
            )
        return

    result = DecisionEngine.get_strategic_advice(
        proposed_increase, current_roas, std_dev, meta_roas, sample_size,
        match_rate, evidence_quality, ctr, cr, frequency, bench_ctr, bench_cr, bench_freq,
        monthly_spend, bias_correction, other_channels
    )

    assert "expected_value_usd" in result
    assert "action" in result
    assert result["action"] in ["STRONG_SCALE", "CAUTIOUS_SCALE", "REDUCE_OR_HOLD"]
    assert "tactical_steps" in result
    assert isinstance(result["expected_value_usd"], float)