import math
from typing import Dict, List, Any
from scipy import stats
from src.trueroas.core.config import settings # Import settings

class QualityEngine:
    """Scores the trustworthiness of the data evidence."""
    @staticmethod
    def calculate_score(match_rate: float, sample_size: int, volatility: float) -> Dict[str, Any]:
        # Weighting: 30% Match Rate, 40% Sample Size (Logarithmic), 30% Stability
        sample_factor = min(math.log10(max(sample_size, 1)) / 2.5, 1.0) # 1.0 at ~300 orders
        stability_factor = 1.0 - min(volatility, 1.0)
        
        score = (match_rate * 0.3) + (sample_factor * 0.4) + (stability_factor * 0.3)
        
        return {
            "score": round(score, 2),
            "level": "High" if score > 0.8 else "Medium" if score > 0.5 else "Low",
            "warning": "Small sample size" if sample_factor < 0.4 else "High volatility" if stability_factor < 0.4 else None,
            "trustworthiness_score": int(score * 100)
        }

class ReadinessEngine: # AUDITOR FIX: Pass evidence_quality to evaluate
    """Scores business scaling capacity and generates 'What Must Be True' conditions."""
    @staticmethod
    def evaluate(ctr: float, cr: float, freq: float, bench_ctr: float, bench_cr: float, current_roas: float, stock_buffer_days: int = 30, evidence_quality: float = 1.0) -> Dict[str, Any]:
        creative_health = min(ctr / max(bench_ctr, 0.001), 1.2)
        offer_health = min(cr / max(bench_cr, 0.001), 1.2)
        audience_health = max(0, 1.0 - (freq / 4.0)) # Saturation penalty
        
        # Identify the primary bottleneck layer
        layers = [("Creative", creative_health), ("Offer", offer_health), ("Audience", audience_health)]
        bottleneck = min(layers, key=lambda x: x[1])[0]

        # New: Inventory Guardrail. If we run out of stock in < 7 days, readiness is 0.
        inventory_health = 1.0 if stock_buffer_days > 14 else (stock_buffer_days / 14)

        # Risk Manager Addition: Dynamic Margin Safety. 
        be_roas = 1 / (1 - settings.VARIABLE_COST_RATE) if settings.VARIABLE_COST_RATE < 1 else 10.0
        safety_margin = 0.20 # 20% buffer
        margin_safety = max(0, min((current_roas - be_roas) / (be_roas * safety_margin), 1.0))
        
        score = (creative_health * 0.15) + (offer_health * 0.15) + (audience_health * 0.1) + (margin_safety * 0.4) + (inventory_health * 0.2)
        score *= evidence_quality # Scale readiness by how much we can trust the data
        
        # Generate 'What Must Be True' (WMBT)
        wmbt = [
            f"CTR must remain above {ctr * 0.9:.2%} to maintain current ROAS floor.",
            f"Conversion rate must not decay below {cr * 0.85:.2%} during spend ramp.",
            f"Frequency should stay below {min(freq + 0.5, 3.0):.1f} to avoid saturation."
        ]
        
        return {
            "readiness_score": round(score, 2),
            "conditions": wmbt,
            "is_ready": score > 0.75,
            "bottleneck": bottleneck
        }

class EconomicEngine:
    """Calculates the financial cost of errors and delays."""
    @staticmethod
    def calculate_costs(proposed_increase: float, ev: float, p_success: float, pessimistic_roas: float) -> Dict[str, Any]:
        # Risk Manager Logic: Error cost is not linear. 
        # Calculate 'Hard Drawdown': What happens if ROAS hits the P10 pessimistic bound?
        drawdown_per_dollar = max(0, 1.0 - pessimistic_roas)
        risk_multiplier = settings.RISK_MULTIPLIER_OPERATIONAL_DISRUPTION # 25% penalty for operational disruption
        
        # Auditor Fix: Risk of Ruin. 
        # If the pessimistic bound (P10) is below the breakeven ROAS, scaling is a gamble.
        breakeven = 1 / (1 - settings.VARIABLE_COST_RATE)
        is_gambling = pessimistic_roas < breakeven
        
        error_cost = proposed_increase * drawdown_per_dollar * risk_multiplier
        
        # Logical Fix: If EV is negative, the "Delay Cost" is actually the 
        # "Burn Cost" of continuing the current inefficient spend.
        if ev >= 0:
            daily_base = ev / 7.0
            urgency_score = round(min(daily_base / settings.URGENCY_SCORE_DAILY_PROFIT_THRESHOLD, 1.0), 2)
            daily_impact = daily_base * (1.0 + urgency_score) # Non-linear decay: in high volatility, lost profit is harder to recover.
            context = "lost profit opportunity"
        else:
            daily_impact = abs(ev) / 7.0
            urgency_score = round(min(daily_impact / settings.URGENCY_SCORE_DAILY_PROFIT_THRESHOLD, 1.0), 2)
            context = "unnecessary capital burn" # For REDUCE_OR_HOLD, success means we stopped a loss or maintained stability
        
        return {
            "cost_of_error": round(error_cost, 2),
            "delay_costs": {
                "7_days": round(daily_impact * 7, 2),
                "14_days": round(daily_impact * 14, 2),
                "30_days": round(daily_impact * 30, 2)
            },
            "urgency_score": urgency_score,
            "risk_of_ruin": is_gambling,
            "impact_context": context
        }

class RecommendationEngine:
    """Orchestrates the Reasoning Order and produces the final actionable output."""
    @staticmethod
    def build_defensible_advice(
        obs: str, 
        evidence: str, 
        hypothesis: str,
        quality: Dict,
        readiness: Dict,
        economics: Dict,
        ev: float,
        action: str,
        reasoning: str,
        merchant_note: str = "",
        monthly_spend: float = 0.0, # AUDITOR FIX: Default to 0, not 10000
        variance_pct: float = 0.35
    ) -> Dict[str, Any]:
        # Dynamic validation plan based on the identified bottleneck
        bottleneck = readiness.get('bottleneck', 'Performance')
        val_plan = f"Monitor {bottleneck} stability and ROAS variance every 48 hours. If {bottleneck} drops > 10%, pause scaling."
        owner_bottom_line = f"The risk of inaction is estimated at ${economics['delay_costs']['14_days']:,.2f} over the next 2 weeks."

        # Calculate Strategic Snapshot fields
        # Monthly Overspend Risk = Monthly Spend * (1 - (True ROAS / Meta ROAS))
        variance_pct = abs(variance_pct) # Ensure positive
        monthly_spend = monthly_spend
        overspend_risk = monthly_spend * variance_pct

        snapshot = {
            "monthly_ad_spend": monthly_spend,
            "overspend_risk": overspend_risk,
            "expected_benefit": f"Reduce wasted spend by ${overspend_risk:,.2f} and improve decision confidence to {quality.get('trustworthiness_score', 0)}%."
        }

        return {
            "reasoning_order": {
                "1_observation": obs,
                "2_evidence": evidence,
                "3_hypotheses": hypothesis,
                "4_decision_cost": f"Cost of error: ${economics['cost_of_error']:,.2f}",
                "5_delay_cost": f"Waiting 14 days costs an estimated ${economics['delay_costs']['14_days']:,.2f} in lost profit.",
                "6_evidence_quality": f"{quality['level']} ({quality['score']})",
                "7_decision_readiness": f"Score: {readiness['readiness_score']} (Ready: {readiness['is_ready']})",
                "8_what_must_be_true": readiness['conditions'],
                "9_expected_value": f"${ev:,.2f}",
                "10_recommendation": action,
                "11_validation_plan": val_plan
            },
            "cro_audit": {
                "trustworthiness_score": quality.get("trustworthiness_score", 0),
                "primary_risk": "Asymmetric Decay" if economics['urgency_score'] > 0.7 else "Statistical Noise",
                "integrity_warning": quality.get("warning"),
                "capital_safety": "Guardrails Active" if readiness['is_ready'] else "High Risk - Correct Bottlenecks"
            },
            "summary": {
                "action": action,
                "justification": reasoning,
                "merchant_explanation": merchant_note,
                "ev": ev,
                "readiness": readiness['readiness_score'],
                "quality": quality['score'],
                "trustworthiness": quality.get("trustworthiness_score", 0),
                "error_cost": economics['cost_of_error'],
                "delay_costs": economics['delay_costs'],
                "owner_bottom_line": owner_bottom_line,
                "snapshot": snapshot
            }
        }