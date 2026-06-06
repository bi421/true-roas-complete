#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import json
import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List

try:
    from cachetools.func import ttl_cache
except ModuleNotFoundError:
    from functools import lru_cache

    def ttl_cache(*args: Any, **kwargs: Any):
        return lru_cache(maxsize=kwargs.get("maxsize", 128))

logger = logging.getLogger("trueroas.strategy")


class StrategyContentService:
    """
    Provides tactical steps and strategic roadmaps tailored for Meta Andromeda
    and Advantage+ synergy.
    Separates presentation logic from core Bayesian inference.
    """

    # Production Optimization: Moved narratives to a dictionary structure
    # that can be easily externalized to a JSON file for i18n/localization.
    NARRATIVE_TEMPLATES = {
        "en": {
            "STRONG_SCALE": "We've identified a verified window for growth. With a {confidence} decision certainty, your current performance is stable enough to absorb more capital. Reconciled data shows a real ROAS of {real_roi}, which supports an aggressive budget lift. The primary focus should be maintaining inventory levels as you scale.",
            "CAUTIOUS_SCALE": "The trend is positive, but the evidence is still stabilizing. While we see a path to {real_roi} ROAS, market volatility suggests a step-by-step approach. We recommend a incremental budget increase while keeping a close watch on {bottleneck} stability over the next 48 hours.",
            "REDUCE_OR_HOLD": "Capital preservation is currently the priority. The system detected a {risk_level} risk level, meaning the attribution signals are currently diverging from bank-truth metrics. To ensure Andromeda scales profitably, we recommend holding spend until the {bottleneck} signals align.",
        }
    }

    @staticmethod
    @ttl_cache(
        maxsize=512, ttl=3600
    )  # Invalidate after 1 hour for Meta API sync parity
    def generate_post_mortem(decision_data_json: str) -> Dict[str, Any]:
        """
        Reports the outcome of business decisions (Profit/Loss) clearly to the Founder.
        """
        try:
            decision_data = json.loads(decision_data_json)
        except Exception as e:
            logger.error(f"Failed to decode decision data for post-mortem: {e}")
            return {"status": "error", "message": "Malformed decision record."}

        # Fix 1, 3 & 5: Handle insufficient data using Decimal precision
        actual_roas_val = (
            decision_data.get("actual_roas_90d")
            or decision_data.get("actual_roas_30d")
            or 0.0
        )
        dec_actual = Decimal(str(actual_roas_val))

        if dec_actual < Decimal("0.1"):
            return {
                "status": "insufficient_data",
                "message": "Verification requires a minimum realized ROAS of 0.1 to prevent statistical bias.",
            }

        # Fix 4: Robust key access
        expected_roas_val = decision_data.get("expected_roas", 0.0)
        assumptions = decision_data.get("assumptions_json", {})
        incremental_spend = assumptions.get("proposed_increase", 0.0)
        meta_roas_at_time = assumptions.get("meta_roas_observed", expected_roas_val)

        dec_expected = Decimal(str(expected_roas_val))
        dec_spend = Decimal(str(incremental_spend))

        outcome = ((dec_actual - dec_expected) * dec_spend).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        outcome_usd = float(outcome)

        # Calculate attribution variance for insights
        actual_roas_float = float(dec_actual)
        variance = (meta_roas_at_time - actual_roas_float) / max(actual_roas_float, 0.1)
        overstatement = max(variance, 0.0)

        return {
            "decision_id": decision_data.get("decision_id", "unknown"),
            "date": decision_data.get("timestamp", "unknown"),
            "action": decision_data.get("action", "unknown"),
            "predicted_success": f"{decision_data.get('confidence_level', 0) * 100:.0f}%",
            "actual_outcome": f"${outcome_usd:,.2f}",
            "verdict": (
                "Verified Growth" if outcome_usd >= 0 else "Budget Leakage Detected"
            ),
            "insight": (
                f"Attribution variance identified at {overstatement:.0%}"
                if overstatement > 0
                else "Direct bank-truth alignment"
            ),
        }

    @staticmethod
    def generate_ai_narrative(
        action: str,
        confidence: str,
        real_roi: str,
        expected_value: str,
        risk_level: str,
        bottleneck: str = "Performance",
        lang: str = "en",
        **_: Any,
    ) -> str:
        """
        Translates cold metrics into a high-level executive narrative.
        Fix 4: Refactored to use templates for easier localization.
        """
        templates = StrategyContentService.NARRATIVE_TEMPLATES.get(
            lang, StrategyContentService.NARRATIVE_TEMPLATES["en"]
        )
        raw_template = templates.get(action, "Analyzing data for patterns...")

        try:
            return raw_template.format(
                confidence=confidence,
                real_roi=real_roi,
                bottleneck=bottleneck,
                risk_level=risk_level,
            )
        except KeyError:
            return "Strategic analysis in progress..."

    @staticmethod
    def get_merchant_verdict(
        action: str,
        variance_pct: float,
        confidence: float,
        incremental_spend: float = 0.0,
        **kwargs: Any,
    ) -> str:
        """
        Translates technical metrics into a one-sentence simple verdict.
        Fix 5: Calculated Capital at Risk dynamically based on spend and variance.
        """
        if action == "REDUCE_OR_HOLD":
            # Link to AdSpendBreaker logic: calculate real exposure
            capital_at_risk = round(incremental_spend * variance_pct, 2)

            if variance_pct > 0.3:
                return f"🛡️ Growth Verification: ${capital_at_risk:,.2f} requires alignment. Attribution signals are {variance_pct:.0%} ahead of bank-truth evidence. Scaling is currently unverified."
            return "🛡️ Risk Mitigation: Maintain current spend. Our Strategic Memory identifies that scaling in these specific conditions has a high historical failure rate."

        if action == "STRONG_SCALE":
            return f"🚀 Verified Opportunity: {confidence:.0%} Decision Accuracy floor. Risk-adjusted EV supports a budget lift with high statistical certainty."

        if action == "CAUTIOUS_SCALE":
            return "⚖️ Note: Positive trend detected, but evidence is still stabilizing. Scale gradually."

        return "Synchronizing data. Please wait."

    @staticmethod
    def get_planning_advice(
        accuracy_score: float, bias: float, trend_delta: float
    ) -> List[str]:
        """Reintroduced missing service method."""
        return [
            f"Historical Accuracy: {accuracy_score}%",
            f"Bias: {bias}",
            f"Trend: {trend_delta}%",
        ]

    @staticmethod
    def get_tactical_steps(
        action: str, incremental_spend: float = 0.0, bottleneck_layer: str = "Performance"
    ) -> List[str]:
        """
        Generates short, actionable tactical steps for the merchant.
        """
        if action == "REDUCE_OR_HOLD":
            return [
                f"🚨 Immediate Action: Pause ad sets exceeding ${incremental_spend:,.2f} daily waste where variance is >30%.",
                f"🔍 Integrity Audit: Cross-reference Shopify Transaction IDs with Meta's {bottleneck_layer} signals.",
                "📉 Capital Preservation: Re-allocate budget to verified stable baseline campaigns."
            ]
        elif action == "STRONG_SCALE":
            return [
                f"🚀 Scale Protocol: Increase daily budget by 15% (Target: +${incremental_spend * 0.15:,.2f}/day).",
                "📊 Vigilance: Monitor real-time Shopify clearing rate vs. Meta's reported ROAS every 6 hours.",
                "🎨 Asset Readiness: Deploy fresh creative iterations to mitigate frequency fatigue during scaling."
            ]
        elif action == "CAUTIOUS_SCALE":
            return [
                "Increase budget by 5-10% gradually.",
                "Monitor ROAS and variance daily.",
                "Test new creative variations to improve efficiency.",
            ]
        return ["Review data and consult with your TrueROAS analyst."]

    @staticmethod
    def get_strategic_roadmap(action: str) -> List[str]:
        """
        Provides a longer-term strategic roadmap for the merchant.
        """
        if action == "STRONG_SCALE":
            return [
                "✅ Step 1: Increase daily budget by 15% in Meta Ads Manager immediately.",
                "✅ Step 2: Upload 2-3 new high-quality images to keep the performance stable.",
                "✅ Step 3: Check your warehouse stock. Ensure you have enough units for the next 30 days.",
            ]
        else:  # REDUCE_OR_HOLD or CAUTIOUS_SCALE
            return [
                "⚠️ Action 1: Pause any ad sets where the ROAS is below 1.5x right now.",
                "⚠️ Action 2: Don't increase budget today. Wait for our next update in 24 hours.",
                "⚠️ Action 3: Review your website checkout flow. People are clicking but not buying as expected.",
            ]

    @staticmethod
    def calculate_profit_optimization_potential(
        platform_roas: float, verified_roas: float, incremental_spend: float
    ) -> Dict[str, Any]:
        """
        Calculates the profit optimization potential by reconciling signals.
        """
        # Logic: If we scale on signals that aren't verified, we risk capital.
        # Reconciling ensures every dollar scaled goes into high-certainty campaigns.
        dec_platform = Decimal(str(platform_roas))
        dec_verified = Decimal(str(verified_roas))
        dec_spend = Decimal(str(incremental_spend))

        preservation = (abs(dec_platform - dec_verified) * dec_spend).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "capital_preservation_usd": float(preservation),
            "verification_multiplier": round(
                platform_roas / max(verified_roas, 0.01), 2
            ),
        }

    @staticmethod
    def get_advantage_plus_scenario_blurb() -> str:
        """
        Highlights synergy with Meta Advantage+.
        """
        return (
            "Scenario: Meta Advantage+ identifies a scaling opportunity and increases daily spend from $2k to $8k. "
            "TrueROAS acts as the financial anchor, reconciling the real-time revenue clearing Shopify. "
            "When the engine detects a variance in attribution, it triggers a guardrail to stabilize spend. "
            "This synergy ensures that Meta's AI scales only when profit is verified in the bank, "
            "maximizing net income and preventing unverified capital exposure."
        )

    @staticmethod
    def get_andromeda_synergy_roadmap() -> List[str]:
        """
        Strategic roadmap for working with Meta's AI algorithms.
        """
        return [
            "Step 1: Allow Meta Advantage+ to identify initial broad signals.",
            "Step 2: Use TrueROAS Bayesian Engine to verify the bank-truth ROAS of those signals.",
            "Step 3: Gradually increase budget floors only when Decision Accuracy exceeds 75%.",
            "Step 4: Maintain automated guardrails to protect capital during platform signal variance.",
        ]
