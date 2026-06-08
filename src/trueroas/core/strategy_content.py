#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import json
import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Union

logger = logging.getLogger("trueroas.strategy")


class StrategyContentService:
    """Provides tactical steps and strategic roadmaps tailored for Meta Andromeda."""

    NARRATIVE_TEMPLATES: Dict[str, Dict[str, str]] = {
        "en": {
            "STRONG_SCALE": (
                "AI Analysis: We've identified a verified window for growth. "
                "With a {confidence} decision certainty, your performance is stable. "
                "Reconciled data shows a real ROAS of {real_roi}. "
                "Suggesting a budget lift of +{scaling_intensity} to maximize returns."
            ),
            "CAUTIOUS_SCALE": (
                "AI Observation: Positive trend detected, but evidence is stabilizing. "
                "Path to {real_roi} ROAS is visible. Recommend a step-by-step {bottleneck} "
                "optimization over the next 48 hours."
            ),
            "REDUCE_OR_HOLD": (
                "AI Alert: Capital preservation is priority. Risk Level: {risk_level}. "
                "Attribution signals are {variance_pct} ahead of bank-truth. "
                "To stop ${capital_bleed_usd} daily bleed, hold spend until signals align."
            ),
        },
        "dashboard": {
            "HEALTHY": (
                "Your capital is deployed efficiently. The variance between platform data and bank-truth "
                "is within acceptable limits. You have a green light to maintain or strategically increase "
                "spend in high-confidence pockets."
            ),
            "WARNING": (
                "We detected a divergence in attribution. Meta is reporting higher success than your bank "
                "account confirms. Suggest holding current budget levels and auditing creative performance "
                "before further scaling."
            ),
            "BLEEDING": (
                "Critical Variance Detected: Your ad spend is currently outpacing verified revenue. "
                "Significant budget waste identified. Immediate reduction of inefficient campaign budgets is "
                "required to protect your margins."
            ),
            "INITIALIZING": (
                "Data Engine Synchronizing: We are currently reconciling your first set of local proofs. "
                "Your strategic roadmap will be available shortly."
            ),
        },
    }

    @staticmethod
    def generate_post_mortem(
        decision_input: Union[Dict[str, Any], str],
    ) -> Dict[str, Any]:
        """Reports the outcome of business decisions (Profit/Loss) clearly to the Founder."""

        if isinstance(decision_input, str):
            decision_data: Dict[str, Any] = json.loads(decision_input)
        else:
            decision_data = decision_input

        actual_roas_val = next(
            (
                decision_data.get(k)
                for k in ["actual_roas_90d", "actual_roas_30d", "actual_roas_7d"]
                if decision_data.get(k) is not None
            ),
            0.0,
        )
        dec_actual = Decimal(str(actual_roas_val))

        if dec_actual < Decimal("0.1"):
            return {
                "status": "insufficient_data",
                "message": (
                    "Verification requires a minimum realized ROAS of 0.1 to maintain statistical integrity."
                ),
            }

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
        scaling_intensity: str = "20%",
        variance_pct: str = "0%",
        capital_bleed_usd: str = "0.00",
        **_: Any,
    ) -> str:
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
                scaling_intensity=scaling_intensity,
                variance_pct=variance_pct,
                capital_bleed_usd=capital_bleed_usd,
            )
        except KeyError:
            return "Strategic analysis in progress..."

    @staticmethod
    def get_dashboard_summary(status: str, lang: str = "en") -> str:
        dashboard_templates = StrategyContentService.NARRATIVE_TEMPLATES["dashboard"]
        return dashboard_templates.get(status, dashboard_templates["INITIALIZING"])

    @staticmethod
    def get_merchant_verdict(
        action: str,
        variance_pct: float,
        confidence: float,
        incremental_spend: float = 0.0,
        **_: Any,
    ) -> str:
        if action == "REDUCE_OR_HOLD":
            capital_at_risk = round(incremental_spend * variance_pct, 2)

            if variance_pct > 0.3:
                return (
                    f"🛡️ Growth Verification: ${capital_at_risk:,.2f} requires alignment. "
                    f"Attribution signals are {variance_pct:.0%} ahead of bank-truth evidence. "
                    "Scaling is currently unverified."
                )
            return (
                "🛡️ Risk Mitigation: Maintain current spend. "
                "Our Strategic Memory identifies that scaling in these specific conditions has a "
                "high historical failure rate."
            )

        if action == "STRONG_SCALE":
            return (
                f"🚀 Verified Opportunity: {confidence:.0%} Decision Accuracy floor. "
                "Risk-adjusted EV supports a budget lift with high statistical certainty."
            )

        if action == "CAUTIOUS_SCALE":
            return "⚖️ Note: Positive trend detected, but evidence is still stabilizing. Scale gradually."

        return "Synchronizing data. Please wait."

    @staticmethod
    def get_planning_advice(
        accuracy_score: float, bias: float, trend_delta: float
    ) -> List[str]:
        return [
            f"Historical Accuracy: {accuracy_score}%",
            f"Bias: {bias}",
            f"Trend: {trend_delta}%",
        ]

    @staticmethod
    def get_tactical_steps(
        action: str,
        incremental_spend: float = 0.0,
        bottleneck_layer: str = "Performance",
    ) -> List[str]:
        if action == "REDUCE_OR_HOLD":
            return [
                f"🚨 Immediate Action: Pause ad sets exceeding ${incremental_spend:,.2f} daily bleed where variance is >30%.",
                f"🔍 Integrity Audit: Cross-reference Shopify Transaction IDs with Meta's {bottleneck_layer} signals.",
                "📉 Capital Preservation: Re-allocate budget to verified stable baseline campaigns.",
            ]
        if action == "STRONG_SCALE":
            return [
                f"🚀 Scale Protocol: Increase daily budget by 15% (Target: +${incremental_spend * 0.15:,.2f}/day).",
                "📊 Vigilance: Monitor real-time Shopify clearing rate vs. Meta's reported ROAS every 6 hours.",
                "🎨 Asset Readiness: Deploy fresh creative iterations to mitigate frequency fatigue during scaling.",
            ]
        if action == "CAUTIOUS_SCALE":
            return [
                "Increase budget by 5-10% gradually.",
                "Monitor ROAS and variance daily.",
                "Test new creative variations to improve efficiency.",
            ]

        return ["Review data and consult with your TrueROAS analyst."]

    @staticmethod
    def get_strategic_roadmap(action: str) -> List[str]:
        if action == "STRONG_SCALE":
            return [
                "✅ Step 1: Increase daily budget by 15% in Meta Ads Manager immediately.",
                "✅ Step 2: Upload 2-3 new high-quality images to keep the performance stable.",
                "✅ Step 3: Check your warehouse stock. Ensure you have enough units for the next 30 days.",
            ]

        return [
            "⚠️ Action 1: Pause any ad sets where the ROAS is below 1.5x right now.",
            "⚠️ Action 2: Don't increase budget today. Wait for our next update in 24 hours.",
            "⚠️ Action 3: Review your website checkout flow. People are clicking but not buying as expected.",
        ]

    @staticmethod
    def calculate_profit_optimization_potential(
        platform_roas: float, verified_roas: float, incremental_spend: float
    ) -> Dict[str, Any]:
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
        return (
            "Scenario: Meta Advantage+ identifies a scaling opportunity and increases daily spend from $2k to $8k. "
            "TrueROAS acts as the financial anchor, reconciling the real-time revenue clearing Shopify. "
            "When the engine detects a variance in attribution, it triggers a guardrail to stabilize spend. "
            "This synergy ensures that Meta's AI scales only when profit is verified in the bank, "
            "maximizing net income and preventing unverified capital exposure."
        )

    @staticmethod
    def get_andromeda_synergy_roadmap() -> List[str]:
        return [
            "Step 1: Allow Meta Advantage+ to identify initial broad signals.",
            "Step 2: Use TrueROAS Bayesian Engine to verify the bank-truth ROAS of those signals.",
            "Step 3: Gradually increase budget floors only when Decision Accuracy exceeds 75%.",
            "Step 4: Maintain automated guardrails to protect capital during platform signal variance.",
        ]
