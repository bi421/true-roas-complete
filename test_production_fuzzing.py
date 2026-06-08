#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import math
from hypothesis import given, strategies as st
from src.trueroas.core.market_decision_engine import MarketDecisionEngine
from src.trueroas.core.inference import BayesianInferenceEngine


class TestProductionMathSafety:
    """
    Final safety gate for production deployment.
    Uses property-based testing to find edge cases in ROI calculations.
    """

    @given(
        platform_roas=st.floats(
            min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
        verified_roas=st.floats(
            min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
        sample_size=st.integers(min_value=0, max_value=100000),
        variance=st.floats(
            min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_bayesian_inference_stability(
        self, platform_roas, verified_roas, sample_size, variance
    ):
        """Ensures the Bayesian engine never returns NaN or non-finite values."""
        engine = BayesianInferenceEngine()
        result = engine.calculate_posterior(
            platform_roas, verified_roas, sample_size, variance
        )

        assert math.isfinite(result["reconciled_roas"])
        assert result["reconciled_roas"] >= 0.0  # Allow 0.0 ROAS (no revenue)
        assert result["reconciled_roas"] <= 1000.1  # Floating point safety margin

        if "confidence_interval" in result:
            for val in result["confidence_interval"]:
                assert math.isfinite(val)

    @given(
        platform_reported_roi=st.floats(
            min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False
        ),
        actual_verified_roi=st.floats(
            min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False
        ),
        sample_size=st.integers(min_value=0, max_value=5000),
        volatility=st.floats(
            min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False
        ),
        ctr=st.floats(min_value=0.0, max_value=1.0),
        cvr=st.floats(min_value=0.0, max_value=1.0),
        current_budget=st.floats(min_value=0.0, max_value=1000000.0),
    )
    def test_market_engine_integrity(
        self,
        platform_reported_roi,
        actual_verified_roi,
        sample_size,
        volatility,
        ctr,
        cvr,
        current_budget,
    ):
        """Ensures the comprehensive diagnostic logic is crash-proof across all inputs."""
        result = MarketDecisionEngine.comprehensive_diagnostic(
            platform_reported_roi=platform_reported_roi,
            actual_verified_roi=actual_verified_roi,
            sample_size=sample_size,
            volatility=volatility,
            ctr=ctr,
            cvr=cvr,
            current_budget=current_budget,
        )

        assert "analysis_report" in result
        assert "executive_ledger" in result
