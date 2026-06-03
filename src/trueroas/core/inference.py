import math
import functools
import random
from scipy import stats
from typing import Tuple, Dict, List, Optional, Any
import numpy as np
import redis
import json
import time
from prometheus_client import Histogram
from pydantic import BaseModel, Field, field_validator
from src.trueroas.core.config import settings
from src.trueroas.services.strategy_content import StrategyContentService
from src.trueroas.core.decision_intelligence import QualityEngine, ReadinessEngine, EconomicEngine, RecommendationEngine

# Global Redis client for caching posterior results
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

BAYESIAN_RECONCILIATION_DURATION = Histogram(
    "bayesian_reconciliation_duration_seconds", 
    "Latency of Bayesian posterior calculations", 
    ["tenant_id"]
)

class DomainError(Exception):
    """Raised for business logic domain violations."""
    pass

class BayesianInput(BaseModel):
    model_config = {"frozen": True}

    tenant_id: str = "default"
    campaign_id: Optional[str] = None
    prior_std: float = Field(default=0.5, gt=0)
    meta_roas: float = Field(..., gt=0, le=1000.0)
    true_roas: float = Field(..., gt=0, le=1000.0)
    std_dev: float = Field(..., gt=0)
    sample_size: int = Field(..., ge=2)
    vertical: Optional[str] = None
    raw_data: Optional[List[float]] = None
    bias_correction: float = 0.0

    @field_validator("std_dev")
    @classmethod
    def std_dev_must_be_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("std_dev must be a finite number")
        return v

class ROASInput(BaseModel):
    current_roas: float = Field(..., description="Reconciled ROAS")
    std_dev: float = Field(..., gt=0)
    sample_size: int = Field(..., ge=1)

    @field_validator("current_roas")
    @classmethod
    def validate_roas_semantics(cls, v: float) -> float:
        if v < 0:
            raise DomainError("Negative ROAS indicates a loss-making campaign that requires manual review, not automated scaling advice.")
        if v == 0:
            raise ValueError("current_roas must be greater than 0")
        return v

class DecisionInput(BaseModel):
    proposed_increase: float = Field(..., gt=0)
    meta_roas: float = Field(..., gt=0)
    current_roas: float = Field(..., gt=0)
    std_dev: float = Field(..., gt=0)
    sample_size: int = Field(..., ge=2)
    match_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_quality: float = Field(default=1.0, ge=0.0, le=1.0)
    monthly_spend: float = Field(default=0.0, ge=0.0)

class BottleneckInput(BaseModel):
    ctr: float = Field(..., ge=0, le=1)
    cr: float = Field(..., ge=0, le=1)
    frequency: float = Field(..., ge=0)

class HistoricalStatsInput(BaseModel):
    current_count: int = Field(..., ge=0)
    current_mean: float
    current_variance: float = Field(..., ge=0)
    new_value: float

def sanitize_metrics(roas: float, sample_size: int, ctr: float, cr: float) -> Tuple[float, int, float, float]:
    """Bounds metrics and rejects impossible values before processing."""
    if not math.isfinite(roas) or not math.isfinite(ctr) or not math.isfinite(cr):
        raise ValueError("Non-finite metrics detected from platform API.")
    if ctr > 1.0 or cr > 1.0:
        raise ValueError("Impossible CTR or Conversion Rate (> 1.0) detected.")
    
    sanitized_roas = max(0.0, min(roas, 1000.0))
    sanitized_sample = max(0, min(int(sample_size), int(1e9)))
    return sanitized_roas, sanitized_sample, ctr, cr

class DecisionEngine:
    @staticmethod
    def update_historical_stats(data: HistoricalStatsInput) -> Tuple[int, float, float, float]:
        """
        Performs a Bayesian-adjacent update using Welford's algorithm to maintain 
        accurate variance and confidence levels as new data arrives.
        """
        current_count, current_mean = data.current_count, data.current_mean
        current_variance, new_value = data.current_variance, data.new_value

        new_count = current_count + 1
        if current_count == 0:
            return new_count, new_value, 0.0, 0.0
            
        delta = new_value - current_mean
        new_mean = current_mean + (delta / new_count)
        if not math.isfinite(new_mean): raise ValueError("Non-finite mean calculated.")
        
        delta2 = new_value - new_mean
        
        # Update M2 (sum of squares of differences from the mean)
        m2 = (current_variance * (current_count - 1) if current_count > 1 else 0) + (delta * delta2)
        # Statistical Hardening: Guard against negative variance
        new_variance = max(m2 / (new_count - 1), 0.0) if new_count > 1 else 0.0
        if not math.isfinite(new_variance): raise ValueError("Non-finite variance calculated.")
        
        # Statistical confidence based on Sample Strength and Stability
        cv = math.sqrt(new_variance) / new_mean if new_mean > 0 else 1.0
        # Use configurable sample size floor from settings
        sample_floor = float(getattr(settings, 'MIN_SAMPLE_SIZE_FOR_CONFIDENCE', 30))
        sample_strength = math.atan(new_count / sample_floor) / (math.pi / 2)
        if not math.isfinite(sample_strength): raise ValueError("Non-finite confidence calculated.")
        stability = 1.0 - min(cv, 1.0)
        
        confidence = round(sample_strength * stability, 4)
        return new_count, new_mean, new_variance, confidence

    @staticmethod
    def calculate_bayesian_posterior(inputs: BayesianInput) -> Dict[str, Any]:
        n = inputs.sample_size
        prior_var = settings.BAYESIAN_DEFAULT_PRIOR_VAR

        # Bessel's correction
        corrected_std = inputs.std_dev * math.sqrt(n / (n - 1)) if n > 1 else inputs.std_dev
        if not math.isfinite(corrected_std): raise ValueError("Bessel correction resulted in non-finite value.")

        data_var = (corrected_std ** 2) / max(n, 1)
        prior_mean = max(inputs.meta_roas + inputs.bias_correction, 0.1)

        if n < 30 and inputs.raw_data:
            # Bootstrap Posterior (fallback): Non-parametric bootstrap (1000 resamples)
            boot_means = np.array([np.mean(np.random.choice(inputs.raw_data, size=n, replace=True)) for _ in range(1000)])
            post_mean = float(np.mean(boot_means))
            post_std = float(np.std(boot_means))
        else:
            # Conjugate Normal
            # Requirement 3.c: Convergence logic. Precision = 1/Variance. 
            # Variance of the mean = std_dev^2 / n.
            precision_prior = 1.0 / prior_var
            precision_data = 1.0 / data_var
            
            post_mean = (prior_mean * precision_prior + inputs.true_roas * precision_data) / (precision_prior + precision_data)
            post_std = math.sqrt(1.0 / (precision_prior + precision_data))
            diagnostic = None

        if not math.isfinite(post_mean) or not math.isfinite(post_std):
            raise ValueError("Bayesian posterior resulted in non-finite values.")

        result = {"post_mean": post_mean, "post_std": post_std, "diagnostic": diagnostic}
        
        # 2. Persist to Redis for Distributed Debugging
        try:
            redis_client.hset(cache_key, mapping={
                "post_mean": str(post_mean),
                "post_std": str(post_std),
                "diagnostic": diagnostic or "None",
                "updated_at": str(time.time())
            })
            redis_client.expire(cache_key, 3600) # 1 hour TTL
        except Exception as e:
            logger.error(f"Failed to cache posterior to Redis: {e}")

        return result

    @staticmethod
    def simulate_outcomes(roas_input: ROASInput) -> dict:
        """Uses SciPy survival function for precise probability of profit calculation."""
        current_roas, std_dev = roas_input.current_roas, roas_input.std_dev
        
        # Probability ROAS > 1.0 using exact Normal SF (Survival Function)
        prob_profit = stats.norm.sf(1.0, loc=current_roas, scale=std_dev)
        
        # Quantile bounds for visual Confidence Fan using ppf (Percent Point Function)
        p10 = stats.norm.ppf(0.1, loc=current_roas, scale=std_dev)
        p90 = stats.norm.ppf(0.9, loc=current_roas, scale=std_dev)

        return {
            "profit_probability": prob_profit,
            "expected_roas": round(current_roas, 2),
            "volatility_index": round(std_dev / current_roas, 2) if current_roas > 0 else 1.0,
            "pessimistic_bound": round(p10, 2),
            "optimistic_bound": round(p90, 2)
        }

    @staticmethod
    def get_strategic_advice(
        data: DecisionInput,
        bottleneck_input: BottleneckInput,
        bench_ctr: float = 0.015,
        bench_cr: float = 0.025,
        bench_freq: float = 2.5,
        bias_correction: float = 0.0,
        other_channels: Dict[str, float] = None,
        raw_data: List[float] = None,
        precomputed_posterior: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculates risk-adjusted Expected Value using Bayesian Posterior.
        """
        if precomputed_posterior:
            post_results = precomputed_posterior
        else:
            # Blend platform priors to create an 'Omnichannel Prior'
            platform_prior = data.meta_roas
            if other_channels:
                total_roas = data.meta_roas + sum(other_channels.values())
                platform_prior = total_roas / (1 + len(other_channels))

            bayesian_input = BayesianInput(
                meta_roas=platform_prior,
                true_roas=data.current_roas,
                std_dev=data.std_dev,
                sample_size=data.sample_size,
                raw_data=raw_data,
                bias_correction=bias_correction
            )
            post_results = DecisionEngine.calculate_bayesian_posterior(bayesian_input)

        return DecisionEngine.get_strategic_advice_from_posterior(
            post_results=post_results,
            data=data,
            bottleneck_input=bottleneck_input,
            bench_ctr=bench_ctr,
            bench_cr=bench_cr,
            bench_freq=bench_freq
        )

    @staticmethod
    def get_strategic_advice_from_posterior(
        post_results: Dict[str, Any],
        data: DecisionInput,
        bottleneck_input: BottleneckInput,
        bench_ctr: float = 0.015, bench_cr: float = 0.025, bench_freq: float = 2.5
    ) -> Dict[str, Any]:
        """Core decision logic using a pre-computed posterior."""
        ctr, cr, frequency = bottleneck_input.ctr, bottleneck_input.cr, bottleneck_input.frequency

        post_roas = post_results["post_mean"]
        post_std = post_results["post_std"]
        
        if post_roas <= 0 or data.sample_size < 5:
            return DecisionEngine._build_insufficient_data_response()

        if not (0.01 <= settings.VARIABLE_COST_RATE <= 0.95):
            raise ValueError(f"VARIABLE_COST_RATE out of bounds: {settings.VARIABLE_COST_RATE}")

        quality_penalty = math.pow(1.1 - evidence_quality, 2)
        channel_overlap_penalty = 1.0 + (0.15 * len(other_channels)) if other_channels else 1.0
        
        uncertainty_adjusted_std = post_std * (1 + (quality_penalty * 8)) * channel_overlap_penalty
        if not math.isfinite(uncertainty_adjusted_std): raise ValueError("Uncertainty propagation non-finite.")
        
        sim = DecisionEngine.simulate_outcomes(ROASInput(current_roas=post_roas, std_dev=uncertainty_adjusted_std, sample_size=sample_size))
        
        readiness = ReadinessEngine.evaluate(ctr, cr, frequency, bench_ctr, bench_cr, current_roas)
        readiness_factor = readiness['readiness_score'] # 0.0 to 1.0

        vol_penalty = sim.get("volatility_index", 0.2)
        decay_base = 0.75 + (0.2 * readiness_factor) # Max 0.95, Min 0.75
        decay_factor = decay_base * math.exp(-vol_penalty * (proposed_increase / max(current_roas * 50, 1)))
        if not math.isfinite(decay_factor): raise ValueError("Decay projection non-finite.")
        marginal_roas = post_roas * max(decay_factor, 0.5)
        
        p_success = stats.norm.sf(1.0, loc=marginal_roas, scale=uncertainty_adjusted_std)
        failure_prob = 1 - p_success
        
        capped_vol = min(sim.get("volatility_index", 0.2), 0.5)
        risk_weight = (0.7 + (capped_vol * 0.8)) / max(match_rate, 0.5)
        
        # Use Marginal ROAS for gain, not Average ROAS.
        potential_gain = proposed_increase * (marginal_roas - 1)
        potential_loss = proposed_increase * min(risk_weight, 1.2)
        
        # Bayesian Weighting: Apply a certainty weight to the EV based on posterior volatility.
        # This represents the 'Certainty Equivalent' of the expected profit.
        posterior_volatility = uncertainty_adjusted_std / post_roas
        certainty_weight = max(0, 1.0 - posterior_volatility)
        expected_value = ((p_success * potential_gain) - (failure_prob * potential_loss)) * certainty_weight
        if not math.isfinite(expected_value): raise ValueError("EV calculation resulted in non-finite value.")

        # Execute Decision Intelligence Engines
        variance_pct = abs(meta_roas - post_roas) / post_roas if post_roas > 0 else 1.0
        hypothesis = "Attribution overlap detected" if variance_pct > 0.2 else "Standard variance"
        
        quality = QualityEngine.calculate_score(match_rate, sample_size, sim['volatility_index'])
        economics = EconomicEngine.calculate_costs(proposed_increase, expected_value, p_success, sim['pessimistic_bound'])

        prior_label = "Blended Platform Prior" if other_channels else "Platform Prior (Meta)"
        evidence_log = [
            {"type": "data", "label": "Bayesian Reconciliation", "value": f"Merged {prior_label} ({platform_prior:.2f}x) and Reconciled ({current_roas:.2f}x) to reach Posterior ROAS of {post_roas:.2f}x."},
            {"type": "calc", "label": "Risk Weighting", "value": f"Applied {risk_weight:.2f}x penalty based on {sim.get('volatility_index', 0):.2%} data volatility."},
            {"type": "calc", "label": "Success Probability", "value": f"{p_success * 100:.1f}% chance of success (adjusted for {evidence_quality * 100:.0f}% data quality)."},
            {"type": "calc", "label": "Channel Overlap", "value": f"Increased uncertainty by {(channel_overlap_penalty-1)*100:.0f}% due to cross-channel attribution risk."},
            {"type": "assumption", "label": "Marginal Decay", "value": "Assumed 15% ROAS decay on new spend based on audience saturation."},
            {"type": "impact", "label": "Certainty-Weighted EV", "value": f"Risk-adjusted return of ${expected_value/proposed_increase if proposed_increase > 0 else 0:.2f} per dollar, weighted by Bayesian certainty ({certainty_weight:.1%})."}
        ]
        
        if post_results.get("diagnostic"):
            evidence_log.append({"type": "warning", "label": "Statistical Reliability", "value": post_results["diagnostic"]})

        # Economic Guardrail: Calculate Safety Margin using Pessimistic Bound (P10)
        breakeven_roas = 1 / (1 - settings.VARIABLE_COST_RATE)
        safety_buffer = sim['pessimistic_bound'] - breakeven_roas

        # Strategic Determination (Strategy Pattern simplified via explicit logical gates)
        action = RecommendationEngine.determine_action(
            p_success=p_success, 
            ev=expected_value, 
            proposed_increase=proposed_increase, 
            safety_buffer=safety_buffer
        )

        # IMPOSSIBLE STATE CHECK: Verification before response delivery
        # Ensures action corresponds to the calculated Expected Value (EV).
        if "SCALE" in action and expected_value <= 0:
            action = "REDUCE_OR_HOLD"
            reasoning = "Action downgraded: Calculated Expected Value (EV) did not support scaling despite high probability."
        else:
            # Map reasoning to the confirmed action
            reasoning = self._generate_reasoning_text(action, sim, breakeven_roas)

        # Distill complex math into merchant-friendly language
        variance_pct = abs(meta_roas - post_roas) / max(post_roas, 1)
        monthly_risk = monthly_spend * variance_pct
        
        merchant_note = f"RECONCILIATION SUMMARY: We identified a ${monthly_risk:,.2f} operational variance in monthly attribution ({variance_pct:.1%} delta). "
        if action == "REDUCE_OR_HOLD":
            merchant_note += f"Based on historical volatility, there is a {p_success:.1%} probability of maintaining the target ROAS floor. Capital preservation is prioritized."
        else:
            merchant_note += f"Verification suggests a {p_success:.1%} confidence level in the projected outcome. Risk-adjusted return is estimated at ${expected_value:,.2f}."

        verification_proof = {
            "bayesian_certainty": f"{certainty_weight:.2%}",
            "pessimistic_loss_cap": f"${potential_loss:,.2f}",
            "model_used": "Empirical Bayes + Bootstrap Fallback" if data.sample_size < 30 else "Conjugate Normal-Normal",
            "diagnostic": post_results.get("diagnostic", "Healthy")
        }

        tactical_steps = StrategyContentService.get_tactical_steps(action, bottleneck_layer=readiness.get('bottleneck', 'Performance'))
        roadmap = StrategyContentService.get_strategic_roadmap(action)

        # Build the final 11-step Reasoning Order
        full_intelligence = RecommendationEngine.build_defensible_advice(
            obs="Reconciling ad-platform reporting with verified store transaction data.",
            evidence=f"Reconciliation variance is {variance_pct*100:.1f}%. Bayesian confidence is {sim['profit_probability']*100:.1f}%.",
            hypothesis=hypothesis,
            quality=quality,
            readiness=readiness,
            economics=economics,
            ev=expected_value,
            action=action,
            reasoning=reasoning,
            monthly_spend=data.monthly_spend,
            variance_pct=variance_pct,
            roadmap=roadmap
        )

        return {
            "expected_value_usd": round(expected_value, 2),
            "action": action,
            "tactical_steps": tactical_steps, # Хэрэглэгчид өгөх 1, 2, 3 алхам
            "reasoning": reasoning,
            "safety_margin": round(safety_buffer, 2),
            "probability": f"{p_success * 100:.1f}%",
            "scenarios": sim,
            "evidence_log": evidence_log,
            "decision_path": full_intelligence["reasoning_order"],
            "intelligence_summary": full_intelligence["summary"],
            "merchant_explanation": merchant_note,
            "audit_verification": verification_proof
        }

    @staticmethod
    def _build_insufficient_data_response() -> Dict[str, Any]:
        """Standard response when statistical significance is not reached."""
        return {
            "expected_value_usd": 0.0,
            "action": "REDUCE_OR_HOLD",
            "reasoning": "Insufficient data or zero ROAS detected. Strategic advice deferred.",
            "safety_margin": 0.0,
            "probability": "0.0%",
            "scenarios": {},
            "status": "insufficient_data",
            "merchant_explanation": "RECONCILIATION SUMMARY: Not enough conversion data yet to provide a reliable recommendation."
        }

    @staticmethod
    def get_action_plan(action: str, bottleneck_layer: str) -> List[Dict]:
        """Standard tactical plans based on strategic direction."""
        if "SCALE" in action:
            return [
                {"task": f"Increase budget by 10-15% while monitoring {bottleneck_layer} health.", "complexity": "Low", "priority": "High"},
                {"task": "Monitor Attribution Variance for the next 48 hours.", "complexity": "Low", "priority": "High"},
                {"task": "Prepare new creative assets for the next scaling phase.", "complexity": "Medium", "priority": "Medium"}
            ]
        return [
            {"task": "Immediately pause underperforming ad sets.", "complexity": "Low", "priority": "Urgent"},
            {"task": f"Resolve {bottleneck_layer} constraints prior to resuming spend.", "complexity": "High", "priority": "High"},
            {"task": "Audit Shopify vs Meta order logs for data discrepancies.", "complexity": "Medium", "priority": "High"}
        ]

    @staticmethod
    def get_full_scenario_analysis(current_spend: float, current_roas: float, std_dev: float, 
                                  meta_roas: float, sample_size: int,
                                  match_rate: float = 1.0, evidence_quality: float = 1.0,
                                  v_rate: float = 0.4, t_rate: float = 0.0):
        """Generates the full scenario table data using posterior statistics."""
        percentages = [-0.1, 0.0, 0.1, 0.2, 0.3]
        results = []

        bayesian_input = BayesianInput(
            meta_roas=meta_roas,
            true_roas=current_roas,
            std_dev=std_dev,
            sample_size=sample_size
        )
        
        # PERFORMANCE FIX: Extract loop-invariant posterior calculation BEFORE the loop.
        post_results = DecisionEngine.calculate_bayesian_posterior(bayesian_input)
        post_roas = post_results["post_mean"]

        for p in percentages:
            increase = current_spend * p
            scenario_spend = current_spend * (1 + p)
            scenario_rev = scenario_spend * post_roas
            net_profit = (scenario_rev * (1 - v_rate - t_rate)) - scenario_spend

            advice = DecisionEngine.get_strategic_advice_from_posterior(
                post_results=post_results,
                data=DecisionInput(
                    proposed_increase=max(increase, 0.01), 
                    meta_roas=meta_roas, 
                    current_roas=current_roas,
                    std_dev=std_dev,
                    sample_size=sample_size,
                    match_rate=match_rate,
                    evidence_quality=evidence_quality
                ),
                bottleneck_input=BottleneckInput(ctr=0.015, cr=0.025, frequency=1.0) # Placeholders for scenario
            )
            results.append({
                "change_pct": f"{int(p*100)}%",
                "action": advice["action"],
                "ev": advice["expected_value_usd"],
                "prob": advice["probability"],
                "net_profit": round(net_profit, 2)
            })
        return results

class GrowthEngine:
    """Constraint identification layer using performance benchmarks."""
    
    @staticmethod
    def calculate_growth_capacity(frequency: float, variance_score: float) -> int:
        saturation = min(max((3.0 - frequency) / 2.0, 0.0), 1.0)
        stability = 1.0 - min(variance_score, 0.8)
        return int((saturation * 0.7 + stability * 0.3) * 100)

    @staticmethod
    def detect_bottleneck(ctr: float, cr: float, frequency: float, 
                          avg_ctr: float = 0.01, avg_cr: float = 0.02, avg_freq: float = 2.5) -> dict:
        evidence = []
        if frequency > avg_freq:
            res = {"layer": "Audience", "issue": "Saturation", "priority": 1}
            evidence.append({"type": "data", "label": "Audience Fatigue", "value": f"Frequency is {frequency:.2f}. Higher than your benchmark."})
        elif ctr < avg_ctr:
            res = {"layer": "Creative", "issue": "Attention/CTR", "priority": 1}
            evidence.append({"type": "data", "label": "Low Engagement", "value": f"CTR is {ctr:.2%}. Below your historical baseline."})
        elif cr < avg_cr:
            res = {"layer": "Offer/Conversion", "issue": "Friction/Offer", "priority": 1}
            evidence.append({"type": "data", "label": "Offer Friction", "value": f"Conversion Rate is {cr:.2%}. Below benchmark; check offer."})
        else:
            res = {"layer": "Financial", "issue": "Capital Efficiency", "priority": 2}
            evidence.append({"type": "calc", "label": "Funnel Health", "value": "Primary constraints are currently budget efficiency."})
        
        res["evidence_log"] = evidence
        return res

    @staticmethod
    def simulate_lever_impact(current_spend: float, current_revenue: float, variable_cost_rate: float, lever_name: str, improvement: float = 0.10) -> dict:
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
    def get_growth_priorities(spend: float, revenue: float, var: float) -> list:
        v_cost = settings.VARIABLE_COST_RATE
        levers = [("Creative (CTR)", 0.15), ("Offer (CR)", 0.10), ("AOV", 0.05), ("Refund Rate", -0.05)]
        opps = []
        for name, imp in levers:
            opps.append(GrowthEngine.simulate_lever_impact(spend, revenue, v_cost, name, imp))
        opps.sort(key=lambda x: x["expected_value"], reverse=True)
        return opps

    @staticmethod
    def get_executive_summary(spend: float, revenue: float, ctr: float, cr: float, freq: float, var: float,
                              bench_ctr: float = 0.01, bench_cr: float = 0.02, bench_freq: float = 2.5) -> dict:
        bottleneck = GrowthEngine.detect_bottleneck(ctr, cr, freq, bench_ctr, bench_cr, bench_freq)
        priorities = GrowthEngine.get_growth_priorities(spend, revenue, var)
        capacity = GrowthEngine.calculate_growth_capacity(freq * (2.5 / max(bench_freq, 1.0)), var)
        return {
            "growth_capacity_score": capacity,
            "primary_constraint": bottleneck,
            "top_action": priorities[0],
            "full_priorities": priorities,
            "recommendation": f"Focus on {priorities[0]['lever']} as the most probable constraint."
        }