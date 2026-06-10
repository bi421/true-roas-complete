#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

from hypothesis import given, strategies as st
from trueroas.learning.auto_tuner import AutoTuner
from typing import List, Tuple


@given(
    predictions=st.lists(
        st.tuples(
            st.floats(
                min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
            ),
            st.booleans(),
        ),
        min_size=1,
        max_size=100,
    )
)
def test_brier_score_bounds_and_type(predictions: List[Tuple[float, bool]]) -> None:
    """Hypothesis test: Brier score must be in [0, 1] for any valid input."""
    score = AutoTuner.calculate_brier_score(predictions)
    assert 0.0 <= score <= 1.0
    assert isinstance(score, float)


def test_brier_monotonicity() -> None:
    """Verify that Brier score increases monotonically with error magnitude."""
    # Case 1: Perfect prediction (0 error)
    perfect = [(1.0, True), (0.0, False)]
    # Case 2: Partial error
    partial = [(0.8, True), (0.2, False)]
    # Case 3: Maximum error
    wrong = [(0.0, True), (1.0, False)]

    score_perfect = AutoTuner.calculate_brier_score(perfect)
    score_partial = AutoTuner.calculate_brier_score(partial)
    score_wrong = AutoTuner.calculate_brier_score(wrong)

    assert score_perfect == 0.0
    assert score_wrong == 1.0
    assert score_perfect < score_partial < score_wrong
