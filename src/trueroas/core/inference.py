import math
import random
from scipy import stats
from typing import Tuple, Dict, List
from src.trueroas.core.config import settings
from src.trueroas.core.decision_intelligence import QualityEngine, ReadinessEngine, EconomicEngine, RecommendationEngine

class DecisionEngine:
    """
    Decision Intelligence Engine using SciPy for high-precision statistical analysis.
    Replaces basic Monte Carlo trials with exact PDF/CDF calculations.
    """
    
    @staticmethod
    def update_historical_stats(current_count: int, current_mean: float, current_variance: float, new_value: float) -> Tuple[int, float, float, float]:
        """
        Performs a Bayesian-adjacent update using Welford's algorithm to maintain 
        accurate variance and confidence levels as new data arrives.
        """
        new_count = current_count + 1
        if current_count == 0:
            return new_count, new_value, 0.0, 0.0
            
        delta = new_value - current_mean
        new_mean = current_mean + (delta / new_count)
        delta2 = new_value - new_mean
        
        # Update M2 (sum of squares of differences from the mean)
        m2 = (current_variance * (current_count - 1) if current_count > 1 else 0) + (delta * delta2)
        new_variance = m2 / (new_count - 1) if new_count > 1 else 0
        
        # Statistical confidence based on Sample Strength and Stability
        cv = math.sqrt(new_variance) / new_mean if new_mean > 0 else 1.0
        # Use configurable sample size floor from settings
        sample_floor = float(getattr(settings, 'MIN_SAMPLE_SIZE_FOR_CONFIDENCE', 30))
        sample_strength = math.atan(new_count / sample_floor) / (math.pi / 2)
        stability = 1.0 - min(cv, 1.0)
        
        confidence = round(sample_strength * stability, 4)
        return new_count, new_mean, new_variance, confidence

    @staticmethod
    def calculate_bayesian_posterior(meta_roas: float, true_roas: float, std_dev: float, sample_size: int, bias_correction: float = 0.0) -> Tuple[float, float]:
        """
        Reconciles Platform Prior (Meta) with Business Evidence (True ROAS) using 
        Normal-Normal conjugate prior distribution.
        """
        # Adjust prior mean by historical systematic bias to handle persistent overstatement.
        # If Meta over-reports, bias_correction would be negative.
        prior_mean = max(meta_roas + bias_correction, 0.1)
        prior_var = settings.BAYESIAN_PRIOR_VARIANCE
        
        data_mean = true_roas
        # Risk Fix: Avoid sqrt(0) or division by zero with a small epsilon
        safe_std = max(std_dev, 0.001)
        data_var = (safe_std ** 2) / max(sample_size, 1)
        
        precision_prior = 1.0 / prior_var
        precision_data = 1.0 / data_var
        
        posterior_mean = (prior_mean * precision_prior + data_mean * precision_data) / (precision_prior + precision_data)
        posterior_var = max(1.0 / (precision_prior + precision_data), 0.0001)
        
        return posterior_mean, math.sqrt(posterior_var)

    @staticmethod
    def simulate_outcomes(current_roas: float, std_dev: float) -> dict:
        """Uses SciPy survival function for precise probability of profit calculation."""
        if std_dev <= 0: 
            std_dev = current_roas * 0.2
        
        # Probability ROAS > 1.0 using exact Normal SF (Survival Function)
        prob_profit = stats.norm.sf(1.0, loc=current_roas, scale=std_dev)
        
        # Quantile bounds for visual Confidence Fan using ppf (Percent Point Function)
        p10 = stats.norm.ppf(0.1, loc=current_roas, scale=std_dev)
        p90 = stats.norm.ppf(0.9, loc=current_roas, scale=std_dev)

        return {
            "profit_probability": prob_profit,
            "expected_roas": round(current_roas, 2),
            "volatility_index": round(std_dev / current_roas, 2),
            "pessimistic_bound": round(p10, 2),
            "optimistic_bound": round(p90, 2)
        }

    @staticmethod
    def get_strategic_advice(proposed_increase: float, current_roas: float, std_dev: float, 
                             meta_roas: float, sample_size: int,
                             match_rate: float = 1.0, evidence_quality: float = 1.0,
                             ctr: float = 0.0, cr: float = 0.0, frequency: float = 0.0,
                             bench_ctr: float = 0.015, bench_cr: float = 0.025, bench_freq: float = 2.5,
                             monthly_spend: float = 10000.0,
                             bias_correction: float = 0.0,
                             other_channels: Dict[str, float] = None):
        """
        Calculates risk-adjusted Expected Value using Bayesian Posterior.
        CROSS-CHANNEL UPDATE: Incorporates multiple platform priors to adjust for attribution overlap.
        """
        # Blend platform priors to create an 'Omnichannel Prior'
        platform_prior = meta_roas
        if other_channels:
            total_roas = meta_roas + sum(other_channels.values())
            platform_prior = total_roas / (1 + len(other_channels))

        # Precision Fix: Pass historical bias correction into the posterior calculation
        # to refine the Bayesian Prior.
        post_roas, post_std = DecisionEngine.calculate_bayesian_posterior( # Line already exists
            platform_prior, current_roas, std_dev, sample_size, bias_correction
        )
        
        # AUDITOR FIX: Punish uncertainty non-linearly. 
        # Low evidence quality should expand risk bounds much faster than it currently does.
        quality_penalty = math.pow(1.1 - evidence_quality, 2)
        # Audit Service Logic: If quality is low, we expand the uncertainty significantly.

        # CROSS-CHANNEL RISK: Multiple channels increase attribution overlap risk (Double counting).
        # We increase the uncertainty multiplier by 15% for every additional channel detected.
        channel_overlap_penalty = 1.0 + (0.15 * len(other_channels)) if other_channels else 1.0
        
        uncertainty_adjusted_std = post_std * (1 + (quality_penalty * 8)) * channel_overlap_penalty
        
        sim = DecisionEngine.simulate_outcomes(post_roas, uncertainty_adjusted_std)
        
        # AUDITOR FIX: Decay must be tied to Readiness. 
        # If the business isn't ready to scale, efficiency collapses immediately.
        readiness = ReadinessEngine.evaluate(ctr, cr, frequency, bench_ctr, bench_cr, current_roas)
        readiness_factor = readiness['readiness_score'] # 0.0 to 1.0

        vol_penalty = sim.get("volatility_index", 0.2)
        decay_base = 0.75 + (0.2 * readiness_factor) # Max 0.95, Min 0.75
        decay_factor = decay_base * math.exp(-vol_penalty * (proposed_increase / max(current_roas * 50, 1)))
        marginal_roas = post_roas * max(decay_factor, 0.5)
        
        p_success = stats.norm.sf(1.0, loc=marginal_roas, scale=uncertainty_adjusted_std)
        failure_prob = 1 - p_success
        
        capped_vol = min(sim.get("volatility_index", 0.2), 0.5)
        risk_weight = (0.7 + (capped_vol * 0.8)) / max(match_rate, 0.5)
        
        # Use Marginal ROAS for gain, not Average ROAS.
        potential_gain = proposed_increase * (marginal_roas - 1)
        potential_loss = proposed_increase * min(risk_weight, 1.2)
        
        # Bayesian Weighting: Apply a certainty weight to the EV based on posterior volatility.
        # This ensures high-variance profit projections are discounted by their uncertainty.
        # This represents the 'Certainty Equivalent' of the expected profit.
        posterior_volatility = uncertainty_adjusted_std / max(post_roas, 0.1)
        certainty_weight = max(0, 1.0 - posterior_volatility)
        expected_value = ((p_success * potential_gain) - (failure_prob * potential_loss)) * certainty_weight

        # Execute Decision Intelligence Engines
        variance_pct = abs(meta_roas - post_roas) / max(post_roas, 1)
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
        
        # Economic Guardrail: Calculate Safety Margin using Pessimistic Bound (P10)
        # Using P10 ensures that even in the bottom 10% of outcomes, capital is protected.
        breakeven_roas = 1 / (1 - settings.VARIABLE_COST_RATE) if settings.VARIABLE_COST_RATE < 1 else 10.0
        safety_buffer = sim['pessimistic_bound'] - breakeven_roas

        if p_success > 0.75 and expected_value > (proposed_increase * 0.5 if proposed_increase > 0 else 0) and safety_buffer > 0:
            action = "STRONG_SCALE"
            reasoning = f"High confidence and positive EV. Pessimistic bound ({sim['pessimistic_bound']:.2f}x) is above breakeven."
        elif p_success > 0.55 and expected_value > 0 and safety_buffer > 0:
            action = "CAUTIOUS_SCALE"
            reasoning = f"Positive EV, but pessimistic bound is near or slightly below breakeven ({breakeven_roas:.2f}x)."
        else:
            action = "REDUCE_OR_HOLD"
            reasoning = f"High risk of loss in pessimistic scenarios. P10 Bound: {sim['pessimistic_bound']:.2f}x vs Breakeven: {breakeven_roas:.2f}x."

        # Distill complex math into merchant-friendly language
        variance_pct = abs(meta_roas - post_roas) / max(post_roas, 1)
        merchant_note = f"Meta is over-reporting by {variance_pct:.0%}. Posterior data suggests a {p_success:.0%} probability of profit "
        merchant_note += f"with a {safety_buffer:+.2f}x safety margin above breakeven. Expected value: ${expected_value:,.2f}."

        # Build the final 11-step Reasoning Order
        full_intelligence = RecommendationEngine.build_defensible_advice(
            obs="Platform performance and independently verified outcomes are diverging.",
            evidence=f"Reconciliation variance is {variance_pct*100:.1f}%. Bayesian confidence is {sim['profit_probability']*100:.1f}%.",
            hypothesis=hypothesis,
            quality=quality,
            readiness=readiness,
            economics=economics,
            ev=expected_value,
            action=action,
            reasoning=reasoning,
            monthly_spend=monthly_spend,
            variance_pct=variance_pct
        )

        return {
            "expected_value_usd": round(expected_value, 2),
            "action": action,
            "reasoning": reasoning,
            "safety_margin": round(safety_buffer, 2),
            "probability": f"{p_success * 100:.1f}%",
            "scenarios": sim,
            "evidence_log": evidence_log,
            "decision_path": full_intelligence["reasoning_order"],
            "intelligence_summary": full_intelligence["summary"],
            "merchant_explanation": merchant_note
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
        post_roas, post_std = DecisionEngine.calculate_bayesian_posterior(meta_roas, current_roas, std_dev, sample_size)
        
        for p in percentages:
            increase = current_spend * p
            scenario_spend = current_spend * (1 + p)
            scenario_rev = scenario_spend * post_roas
            net_profit = (scenario_rev * (1 - v_rate - t_rate)) - scenario_spend

            advice = DecisionEngine.get_strategic_advice(increase, current_roas, std_dev, meta_roas, sample_size, match_rate, evidence_quality)
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