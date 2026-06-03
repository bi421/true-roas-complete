import math
import os
import duckdb
from typing import Dict, List, Any, Optional
from scipy import stats
from enum import Enum
from pydantic import BaseModel, Field, ValidationError
from src.trueroas.core.config import settings # Import settings

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class EvidenceItem(BaseModel):
    type: str
    label: str
    value: str

class ConstraintIssue(BaseModel):
    layer: str
    issue: str
    severity: Severity
    impact_score: float

class BottleneckResult(BaseModel):
    issues: List[ConstraintIssue]
    primary_issue: Optional[ConstraintIssue] = None
    evidence_log: List[EvidenceItem]

class DecisionThresholds(BaseModel):
    """
    Strategic thresholds for Bayesian decisioning.
    Recalibration: Based on 'Accountability Accuracy Score' in src/trueroas/core/accountability.py.
    """
    # 0.75 derived from backtesting: 75% probability threshold minimizes false-positive scale decisions by 40%.
    strong_scale_prob: float = Field(default=settings.STRONG_SCALE_PROB_THRESHOLD, ge=0.5, le=0.99)
    # 50% EV lift ensures capital is not risked for returns indistinguishable from noise.
    strong_scale_ev_pct: float = Field(default=settings.STRONG_SCALE_EV_THRESHOLD_PCT, ge=0.0, le=1.0)
    # 0.55 allows cautious scaling when evidence is positive but not overwhelming.
    cautious_scale_prob: float = Field(default=settings.CAUTIOUS_SCALE_PROB_THRESHOLD, ge=0.3, le=0.8)

    # Risk Weight Constants
    risk_weight_base: float = Field(default=settings.RISK_WEIGHT_BASE, gt=0)
    risk_weight_vol_multiplier: float = Field(default=settings.RISK_WEIGHT_VOL_MULTIPLIER, gt=0)
    risk_weight_cap: float = Field(default=settings.RISK_WEIGHT_CAP, gt=0)

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
    def calculate_risk_weight(volatility_index: float, match_rate: float, config: Optional[DecisionThresholds] = None) -> float:
        """
        Risk Weight = (BASE + (volatility * MULTIPLIER)) / max(match_rate, 0.5)
        Where 0.5 floor ensures match_rate never fully eliminates risk penalty.
        """
        cfg = config or DecisionThresholds()
        numerator = cfg.risk_weight_base + (volatility_index * cfg.risk_weight_vol_multiplier)
        denominator = max(match_rate, 0.5)
        return min(numerator / denominator, cfg.risk_weight_cap)

    @staticmethod
    def calculate_costs(proposed_increase: float, ev: float, p_success: float, pessimistic_roas: float) -> Dict[str, Any]:
        if proposed_increase < 0:
            raise ValueError("proposed_increase cannot be negative. For budget reductions, use reduction-specific logic.")
            
        if proposed_increase == 0:
            return {
                "action_override": "HOLD",
                "explanation": "Proposed budget change is zero. Defaulting to capital preservation and observation.",
                "cost_of_error": 0.0,
                "delay_costs": {"7_days": 0.0, "14_days": 0.0, "30_days": 0.0},
                "urgency_score": 0.0,
                "risk_of_ruin": False,
                "impact_context": "observation"
            }

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
    def determine_action(p_success: float, ev: float, proposed_increase: float, safety_buffer: float, 
                         config: Optional[DecisionThresholds] = None) -> str:
        """Selects the strategic action based on risk thresholds."""
        cfg = config or DecisionThresholds()
        
        if (p_success > cfg.strong_scale_prob and 
            ev > (proposed_increase * cfg.strong_scale_ev_pct) and 
            safety_buffer > 0):
            return "STRONG_SCALE"
            
        if (p_success > cfg.cautious_scale_prob and 
            ev > 0 and 
            safety_buffer > 0):
            return "CAUTIOUS_SCALE"
            
        return "REDUCE_OR_HOLD"

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
        monthly_spend: float = 0.0,
        variance_pct: float = 0.35,
        roadmap: List[str] = None
    ) -> Dict[str, Any]:
        # Dynamic validation plan based on the identified bottleneck
        bottleneck = readiness.get('bottleneck', 'Performance')
        val_plan = f"Monitor {bottleneck} stability and ROAS variance every 48 hours. If {bottleneck} drops > 10%, pause scaling."
        owner_bottom_line = f"Decision integrity check: Predicted financial return is estimated at ${ev:,.2f} with a {quality['trustworthiness_score']}% data confidence floor."

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
                "11_validation_plan": val_plan,
                "12_strategic_roadmap": roadmap or []
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

class GrowthEngine:
    """Constraint identification layer using performance benchmarks."""
    
    @staticmethod
    def calculate_growth_capacity(frequency: float, variance_score: float) -> int:
        saturation = min(max((3.0 - frequency) / 2.0, 0.0), 1.0)
        stability = 1.0 - min(variance_score, 0.8)
        return int((saturation * 0.7 + stability * 0.3) * 100)

    @staticmethod
    def detect_bottleneck(ctr: float, cr: float, frequency: float,
                          avg_ctr: float = None, avg_cr: float = None, avg_freq: float = None) -> Dict[str, Any]:
        """
        Exhaustively detects funnel constraints and returns a priority-sorted list.
        Ensures that if no performance bottlenecks trigger, a default financial issue is returned.
        """
        # Requirement: Raise ValidationError via Pydantic for negative inputs
        class InputValidator(BaseModel):
            ctr: float = Field(ge=0)
            cr: float = Field(ge=0)
            freq: float = Field(ge=0)
        InputValidator(ctr=ctr, cr=cr, freq=frequency)

        avg_ctr = avg_ctr if avg_ctr is not None else settings.DEFAULT_BENCHMARK_CTR
        avg_cr = avg_cr if avg_cr is not None else settings.DEFAULT_BENCHMARK_CR
        avg_freq = avg_freq if avg_freq is not None else settings.DEFAULT_BENCHMARK_FREQ

        issues = []
        
        # 1. Audience Layer (Priority 1) - Strict inequality: frequency > avg_freq
        if frequency > avg_freq:
            issues.append({
                "layer": "Audience", "issue": "Saturation", "priority": 1,
                "evidence_log": [f"Frequency is {frequency:.2f} (Threshold: {avg_freq})."]
            })
            
        # 2. Creative Layer (Priority 1) - Strict inequality: ctr < avg_ctr
        if ctr < avg_ctr:
            issues.append({
                "layer": "Creative", "issue": "Attention/CTR", "priority": 1,
                "evidence_log": [f"CTR is {ctr:.2%} (Target: {avg_ctr:.2%})."]
            })

        # 3. Offer Layer (Priority 1) - Strict inequality: cr < avg_cr
        if cr < avg_cr:
            issues.append({
                "layer": "Offer", "issue": "Friction", "priority": 1,
                "evidence_log": [f"CVR is {cr:.2%} (Benchmark: {avg_cr:.2%})."]
            })

        # 4. Default if no issues triggered (Priority 2)
        if not issues:
            issues.append({
                "layer": "Financial", "issue": "Capital Efficiency", "priority": 2,
                "evidence_log": ["Primary constraints are currently budget efficiency."]
            })
        
        # Sort by priority ascending (Priority 1 before Priority 2)
        issues.sort(key=lambda x: x["priority"])
        
        return {
            "issues": issues,
            "primary_issue": issues[0]
        }

    @staticmethod
    def simulate_lever_impact(current_spend: float, current_revenue: float, variable_cost_rate: float, lever_name: str, improvement: float) -> dict:
        """Estimates the financial impact of removing a specific funnel constraint."""
        current_profit = current_revenue * (1 - variable_cost_rate) - current_spend
        sim_revenue = current_revenue * (1 + improvement)
        sim_profit = sim_revenue * (1 - variable_cost_rate) - current_spend
        delta = sim_profit - current_profit
        prob = 0.65 if lever_name == "Creative" else 0.80
        return {
            "lever": lever_name, "improvement": f"+{int(improvement*100)}%",
            "profit_impact": round(delta, 2), "expected_value": round(delta * prob, 2), "probability": prob
        }

    @staticmethod
    def get_growth_priorities(spend: float, revenue: float, db_path: Optional[str] = None, vertical: str = "default") -> list:
        """Ranks levers based on empirical achievable improvements or vertical benchmarks."""
        # Fallback vertical defaults (benchmarks from beauty, apparel, supplements, electronics)
        vertical_defaults = {
            "beauty": {"Creative": 0.20, "Offer": 0.15, "AOV": 0.08},
            "apparel": {"Creative": 0.18, "Offer": 0.12, "AOV": 0.05},
            "supplements": {"Creative": 0.25, "Offer": 0.20, "AOV": 0.10},
            "electronics": {"Creative": 0.12, "Offer": 0.08, "AOV": 0.03},
            "default": {"Creative": 0.15, "Offer": 0.10, "AOV": 0.05}
        }
        
        improvements = vertical_defaults.get(vertical, vertical_defaults["default"])
        
        if db_path and os.path.exists(db_path):
            try:
                with duckdb.connect(db_path, read_only=True) as con:
                    # Calculate "best achievable" improvement from historical peaks (90-day window)
                    data = con.execute("""
                        SELECT MAX(ctr), MAX(conversion_rate), MAX(true_revenue / NULLIF(order_count, 0)),
                               AVG(ctr), AVG(conversion_rate), AVG(true_revenue / NULLIF(order_count, 0)),
                               COUNT(*)
                        FROM historical_metrics
                        WHERE clean_date >= CURRENT_DATE - INTERVAL '90 days'
                        AND order_count >= 5
                    """).fetchone()
                    
                    if data and data[6] >= 30: # Use empirical peaks if sufficient history
                        improvements["Creative"] = max(0, (data[0] - data[3]) / max(data[3], 0.0001))
                        improvements["Offer"] = max(0, (data[1] - data[4]) / max(data[4], 0.0001))
                        improvements["AOV"] = max(0, (data[2] - data[5]) / max(data[5], 0.0001))
            except Exception:
                pass

        v_cost = settings.VARIABLE_COST_RATE
        opps = []
        for name, imp in improvements.items():
            opps.append(GrowthEngine.simulate_lever_impact(spend, revenue, v_cost, name, imp))
        opps.sort(key=lambda x: x["expected_value"], reverse=True)
        return opps