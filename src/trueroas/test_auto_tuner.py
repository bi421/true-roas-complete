from hypothesis import given, strategies as st
from trueroas.learning.auto_tuner import AutoTuner


def test_brier_score_logic() -> None:
    # Perfect prediction
    assert AutoTuner.calculate_brier_score([(1.0, True), (0.0, False)]) == 0.0
    # Total failure
    assert AutoTuner.calculate_brier_score([(1.0, False), (0.0, True)]) == 1.0


@given(
    current=st.floats(min_value=0.4, max_value=1.5),
    brier=st.floats(min_value=0.0, max_value=1.0),
    bias=st.floats(min_value=-1.0, max_value=1.0),
    n=st.integers(min_value=0, max_value=1000),
)
def test_threshold_bounds(current: float, brier: float, bias: float, n: int) -> None:
    new_t = AutoTuner.compute_new_threshold(current, brier, bias, n)
    assert 0.4 <= new_t <= 1.5


def test_systematic_bias_direction() -> None:
    # Over-optimistic: predicted 0.9, actual False (0.0) -> Bias = 0.9
    predictions = [(0.9, False)] * 10
    bias = AutoTuner.detect_systematic_bias(predictions)
    assert bias > 0
