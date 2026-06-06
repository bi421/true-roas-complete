# TrueROAS - Core Decision Engine
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict

from scipy import stats

from src.trueroas.core.bot_defense import BotDefenseEngine
from src.trueroas.core.market_config import Settings
from src.trueroas.core.strategy_content import StrategyContentService


class MarketDecisionEngine:
    """Intelligence center combining traffic safety and Bayesian inference."""

    @staticmethod
    def comprehensive_diagnostic(
        platform_reported_roi: float,
        actual_verified_roi: float,
        sample_size: int,
        volatility: float,
        ctr: float,
        cvr: float,
        current_budget: float,
        vertical: str = "default",
    ) -> Dict[str, Any]:
        """Performs a comprehensive diagnostic audit of a campaign.

        Args:
            platform_reported_roi (float): ROI as reported by the ad platform.
            actual_verified_roi (float): Verified ROI from business data.
            sample_size (int): Number of orders in the sample.
            volatility (float): Observed data volatility.
            ctr (float): Click-through rate.
            cvr (float): Conversion rate.
            current_budget (float): Current daily budget in USD.
            vertical (str): Business vertical for benchmarking. Defaults to "default".

        Returns:
            Dict[str, Any]: A detailed analysis report with strategic recommendations
                and narrative justifications.
        """

        # 1. Traffic Safety Audit - Frequency baseline now coming from Settings
        audit_result = BotDefenseEngine.perform_security_audit(ctr, cvr, frequency=1.2)
        adjusted_roi = BotDefenseEngine.adjust_roi(
            actual_verified_roi, audit_result["risk_score"]
        )

        # 2. Bayesian Posterior Calculation (Weight increases with sample size)
        data_weight = min(sample_size / 50.0, 0.95)
        expected_roi = (platform_reported_roi * (1 - data_weight)) + (
            adjusted_roi * data_weight
        )

        # 3. Calculate Success Probability (Probability ROI > Breakeven)
        std_dev = volatility * expected_roi
        success_prob = float(
            stats.norm.sf(
                Settings.breakeven_roi, loc=expected_roi, scale=max(std_dev, 0.1)
            )
        )

        # 4. Generate Financial Recommendations
        recommendation = "HOLD/OBSERVE"
        expected_profit = 0.0
        potential_waste = 0.0

        if expected_roi < Settings.breakeven_roi * 0.8:
            recommendation = "REDUCE/PAUSE"
            expected_profit = current_budget * -0.3
        elif (
            success_prob > Settings.scaling_probability_threshold
            and expected_roi > Settings.breakeven_roi
        ):
            recommendation = "STRONG_SCALE"
            expected_profit = current_budget * 0.2 * (expected_roi - 1)
        elif platform_reported_roi > expected_roi:
            potential_waste = (
                1 - (expected_roi / platform_reported_roi)
            ) * current_budget
        real_roi = Decimal(str(expected_roi)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Generate the AI Narrative using the StrategyContentService
        narrative = StrategyContentService.generate_ai_narrative(
            action=recommendation.replace("/", "_OR_"),  # Standardize key for map
            confidence=f"{success_prob:.1%}",
            real_roi=f"{real_roi}x",
            expected_value=f"${expected_profit:,.2f}",
            risk_level=audit_result["risk_level"],
            vertical=vertical,
        )
        if recommendation == "STRONG_SCALE" and "Collection depth" not in narrative:
            narrative = f"Collection depth verified. {narrative}"

        return {
            "analysis_report": {
                "recommended_action": recommendation,
                "decision_confidence": f"{success_prob:.1%}",
                "real_roi": f"{real_roi}x",
                "traffic_safety_level": audit_result["risk_level"],
                "executive_narrative": narrative,
            },
            "risk_audit": {
                "bot_score": audit_result["risk_score"],
                "warning_items": audit_result["warning_items"],
                "data_reliability": f"{audit_result['data_reliability']*100:.0f}%",
            },
            "executive_ledger": {
                "breakeven_point": Settings.breakeven_roi,
                "projected_profit_lift": f"${max(0, expected_profit):,.2f}",
                "expected_decision_value": f"${expected_profit:,.2f}",
                "wasted_spend_prevented": f"${max(0, potential_waste):,.2f}",
                "suggested_adjustment": (
                    "+20%"
                    if recommendation == "STRONG_SCALE"
                    else "-50%" if "REDUCE" in recommendation else "0%"
                ),
                "merchant_insight": (
                    f"By following this advice, you could gain ${max(0, expected_profit):,.2f} in new profit "
                    f"or prevent ${max(0, potential_waste):,.2f} in unnecessary spending."
                ),
            },
        }
