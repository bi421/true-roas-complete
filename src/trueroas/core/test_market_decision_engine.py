#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

from src.trueroas.core.market_config import Settings
from src.trueroas.core.market_decision_engine import MarketDecisionEngine


class TestMarketDecisionEngine:
    """
    Unit tests for MarketDecisionEngine to ensure English parameter refactoring
    and strategic decision logic are working as expected.
    """

    def test_strong_scale_scenario(self):
        """
        Verifies that high-performing campaigns with high confidence trigger STRONG_SCALE.
        Scenario: Platform ROAS 4.0, Verified 3.5, Large Sample Size (Weight 0.95).
        """
        result = MarketDecisionEngine.comprehensive_diagnostic(
            platform_reported_roi=4.0,
            actual_verified_roi=3.5,
            sample_size=100,
            volatility=0.1,
            ctr=0.02,  # Safe CTR
            cvr=0.03,  # Safe CVR
            current_budget=1000.0,
            vertical="apparel",
        )

        report = result["analysis_report"]
        ledger = result["executive_ledger"]

        assert report["recommended_action"] == "STRONG_SCALE"
        assert report["traffic_safety_level"] == "Safe"
        # expected_roi = (4.0 * 0.05) + (3.5 * 0.95) = 3.525
        assert report["real_roi"] == "3.53x"
        assert "Collection depth" in report["executive_narrative"]
        assert ledger["breakeven_point"] == Settings.breakeven_roi
        assert "$" in ledger["expected_decision_value"]

    def test_reduce_pause_on_low_roi(self):
        """
        Verifies that campaigns significantly below the breakeven threshold trigger REDUCE/PAUSE.
        """
        result = MarketDecisionEngine.comprehensive_diagnostic(
            platform_reported_roi=1.5,
            actual_verified_roi=1.0,  # Below breakeven * 0.8 (1.336)
            sample_size=100,
            volatility=0.2,
            ctr=0.015,
            cvr=0.02,
            current_budget=500.0,
        )

        assert result["analysis_report"]["recommended_action"] == "REDUCE/PAUSE"
        assert result["executive_ledger"]["suggested_adjustment"] == "-50%"

    def test_bot_traffic_penalization(self):
        """
        Verifies that high bot risk (abnormally high CTR) results in an ROI penalty
        and critical safety warning.
        """
        # ctr=0.12 exceeds the 0.08 threshold in Settings
        result = MarketDecisionEngine.comprehensive_diagnostic(
            platform_reported_roi=5.0,
            actual_verified_roi=4.0,
            sample_size=100,
            volatility=0.1,
            ctr=0.12,  # Critical Bot Risk
            cvr=0.001,
            current_budget=1000.0,
        )

        report = result["analysis_report"]
        audit = result["risk_audit"]

        assert report["traffic_safety_level"] == "Critical"
        assert audit["bot_score"] >= 0.8
        # actual_verified_roi 4.0 penalized by 0.4 multiplier = 1.6
        # expected_roi = (5.0 * 0.05) + (1.6 * 0.95) = 0.25 + 1.52 = 1.77
        assert report["real_roi"] == "1.77x"

    def test_hold_observe_on_high_volatility(self):
        """
        Verifies that high volatility reduces success probability, leading to a HOLD/OBSERVE status.
        """
        result = MarketDecisionEngine.comprehensive_diagnostic(
            platform_reported_roi=2.0,
            actual_verified_roi=1.8,
            sample_size=20,  # Low weight
            volatility=0.6,  # High noise
            ctr=0.015,
            cvr=0.025,
            current_budget=1000.0,
        )

        assert result["analysis_report"]["recommended_action"] == "HOLD/OBSERVE"
        assert result["executive_ledger"]["suggested_adjustment"] == "0%"

    def test_data_reliability_reporting(self):
        """Checks if data reliability percentage is correctly calculated and reported."""
        result = MarketDecisionEngine.comprehensive_diagnostic(
            4.0, 3.0, 50, 0.2, 0.02, 0.03, 1000.0
        )
        # risk_score 0.0 -> reliability 1.0 (100%)
        assert result["risk_audit"]["data_reliability"] == "100%"
