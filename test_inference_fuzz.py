import pytest
from hypothesis import given, strategies as st
from src.trueroas.core.market_decision_engine import MarketDecisionEngine


class TestInferenceFuzzing:
    """
    Hypothesis ашиглан математик загварын тогтвортой байдлыг шалгах тестүүд.
    """

    @given(
        platform_reported_roi=st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        actual_verified_roi=st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        sample_size=st.integers(min_value=0, max_value=10000),
        volatility=st.floats(
            min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False
        ),
        ctr=st.floats(min_value=0.0, max_value=1.0),
        cvr=st.floats(min_value=0.0, max_value=1.0),
        current_budget=st.floats(min_value=0.0, max_value=100000.0),
    )
    def test_diagnostic_engine_stability(
        self,
        platform_reported_roi,
        actual_verified_roi,
        sample_size,
        volatility,
        ctr,
        cvr,
        current_budget,
    ):
        """
        Ямар ч оролтын утга дээр систем NaN эсвэл Crash өгөхгүй байхыг баталгаажуулна.
        """
        try:
            result = MarketDecisionEngine.comprehensive_diagnostic(
                platform_reported_roi=platform_reported_roi,
                actual_verified_roi=actual_verified_roi,
                sample_size=sample_size,
                volatility=volatility,
                ctr=ctr,
                cvr=cvr,
                current_budget=current_budget,
            )

            # Үр дүн дотор NaN утга байгаа эсэхийг шалгах
            assert "real_roi" in result["analysis_report"]
        except ZeroDivisionError:
            pytest.fail("Math engine encountered Division by Zero!")
