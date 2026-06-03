#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

from typing import List, Dict, Any

class StrategyContentService:
    """
    Provides tactical steps and strategic roadmaps based on decision actions.
    Separates presentation logic from core Bayesian inference.
    """

    @staticmethod
    def get_merchant_verdict(action: str, variance_pct: float, confidence: float) -> str:
        """
        Translates technical metrics into a one-sentence simple verdict.
        """
        if action == "REDUCE_OR_HOLD":
            if variance_pct > 0.3:
                return f"⚠️ Risk: Meta ROAS is overstated by {variance_pct:.0%}. Scaling now risks ${spend_at_risk:,.0f} in capital efficiency loss."
            return "Advice: Maintain current budget until sales data stabilizes."
        
        if action == "STRONG_SCALE":
            return f"🚀 Opportunity: High {confidence:.0%} confidence in outcome. Safely increase budget."
            
        if action == "CAUTIOUS_SCALE":
            return "⚖️ Note: Positive trend detected, but evidence is still stabilizing. Scale gradually."
            
        return "Synchronizing data. Please wait."

    @staticmethod
    def get_tactical_steps(action: str, bottleneck_layer: str = "Performance") -> List[str]:
        """
        Generates short, actionable tactical steps for the merchant.
        """
        if action == "REDUCE_OR_HOLD":
            return [
                "Immediately pause underperforming ad sets.",
                "Audit Shopify vs Meta order logs for data discrepancies.",
                f"Resolve {bottleneck_layer} constraints prior to resuming spend."
            ]
        elif action == "STRONG_SCALE":
            return [
                "Increase budget by 15% immediately.",
                "Monitor CTR and Conversion Rate every 12 hours.",
                "Prepare new creative assets for the next scaling phase."
            ]
        elif action == "CAUTIOUS_SCALE":
            return [
                "Increase budget by 5-10% gradually.",
                "Monitor ROAS and variance daily.",
                "Test new creative variations to improve efficiency."
            ]
        return ["Review data and consult with your TrueROAS analyst."]

    @staticmethod
    def get_strategic_roadmap(action: str) -> List[str]:
        """
        Provides a longer-term strategic roadmap for the merchant.
        """
        if action == "STRONG_SCALE":
            return [
                "Support the platform's Learning Phase and maintain steady budget increases.",
                "Provide more creative assets to Meta's Advantage+ algorithm to improve competitiveness.",
                "Plan inventory for 30 days to ensure sales fulfillment success."
            ]
        else: # REDUCE_OR_HOLD or CAUTIOUS_SCALE
            return [
                "Focus on improving data collection quality and Attribution Alignment.",
                "Leverage Meta's power for new customer acquisition while using email marketing to increase LTV.",
                "Improve the product offer and website user experience to protect marketing ROI."
            ]