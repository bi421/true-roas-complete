#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
from trueroas.core.inference import BayesianInferenceEngine
from trueroas.core.decision_intelligence import (
    QualityEngine,
    ReadinessEngine,
    EconomicEngine,
    BotGuardEngine,
    GrowthEngine,
    RecommendationEngine,
)
from trueroas.core.config import settings
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger("trueroas.orchestrator")

# Prometheus Metrics Definitions
PIPELINE_STAGE_LATENCY = Histogram(
    "trueroas_pipeline_stage_latency_seconds",
    "Latency of each decision pipeline stage",
    ["stage"],
)

DECISION_RESULTS = Counter(
    "trueroas_decision_results_total",
    "Total count of decisions made by the orchestrator",
    ["tenant_id", "action"],
)

DECISION_SCORES = Gauge(
    "trueroas_decision_scores",
    "Current quality and readiness scores for decisions",
    ["tenant_id", "metric_type"],
)

PIPELINE_ERRORS = Counter(
    "trueroas_pipeline_errors_total",
    "Total count of exceptions in the decision pipeline",
    ["tenant_id", "error_type"],
)


class DecisionContext(BaseModel):
    tenant_id: str = Field(..., min_length=1, description="Unique tenant identifier")
    campaign_id: str = Field(..., min_length=1, description="Ad platform campaign ID")
    platform_roas: float = Field(
        ..., ge=0, description="ROAS as reported by the ad platform"
    )
    verified_roas: float = Field(
        ..., ge=0, description="Verified ROAS from actual revenue"
    )
    spend: float = Field(..., ge=0, description="Total ad spend in currency")
    revenue: float = Field(..., ge=0, description="Total verified revenue")
    sample_size: int = Field(
        ..., ge=0, description="Order count used for statistical weight"
    )
    variance: float = Field(..., ge=0, description="Order value variance")
    ctr: float = Field(..., ge=0, description="Click-through rate (decimal)")
    cr: float = Field(..., ge=0, description="Conversion rate (decimal)")
    frequency: float = Field(..., ge=0, description="Ad frequency")
    inventory_days: int = Field(
        default=30, ge=0, description="Estimated stock remaining in days"
    )
    vertical: str = Field(
        default="default", description="Business category for benchmarking"
    )
    scale_factor: float = Field(
        default=1.5, ge=0.1, le=5.0, description="FTC Safeguard: Limits budget spikes"
    )


class DecisionOrchestrator:
    """
    The Single Source of Truth for all strategic decisions.
    Unifies Bayesian math, traffic safety, and business readiness.
    """

    def __init__(self) -> None:
        self.inference_engine = BayesianInferenceEngine()

    async def execute_audit(self, ctx: DecisionContext) -> Dict[str, Any]:
        """Executes the full decision pipeline audit for a campaign.

        Args:
            ctx (DecisionContext): The campaign context and observed metrics.

        Returns:
            Dict[str, Any]: The final strategic recommendation and defensible advice.
        """
        logger.info(f"Initiating Unified Decision Pipeline for {ctx.campaign_id}")

        try:
            # 1. Traffic Safety & Data Quality
            with PIPELINE_STAGE_LATENCY.labels(stage="traffic_safety").time():
                bot_info = BotGuardEngine.analyze_bot_risk(
                    ctx.ctr, ctx.cr, ctx.frequency
                )
                quality = QualityEngine.calculate_score(
                    match_rate=ctx.verified_roas / max(ctx.platform_roas, 0.01),
                    sample_size=ctx.sample_size,
                    volatility=ctx.variance,
                )
            DECISION_SCORES.labels(tenant_id=ctx.tenant_id, metric_type="quality").set(
                quality["score"]
            )

            # 2. Bayesian Reconciliation (The Math)
            with PIPELINE_STAGE_LATENCY.labels(stage="bayesian_reconciliation").time():
                # Penalize verified_roas if bot risk is high
                adjusted_verified = ctx.verified_roas * (
                    0.5 if not bot_info["is_clean"] else 1.0
                )
                posterior = self.inference_engine.calculate_posterior(
                    platform_roas=ctx.platform_roas,
                    verified_roas=adjusted_verified,
                    sample_size=ctx.sample_size,
                    variance=ctx.variance,
                )

            # 3. Readiness & Funnel Constraints
            with PIPELINE_STAGE_LATENCY.labels(stage="readiness_evaluation").time():
                readiness = ReadinessEngine.evaluate(
                    ctr=ctx.ctr,
                    cr=ctx.cr,
                    freq=ctx.frequency,
                    bench_ctr=settings.DEFAULT_BENCHMARK_CTR,
                    bench_cr=settings.DEFAULT_BENCHMARK_CR,
                    current_roas=posterior["reconciled_roas"],
                    stock_buffer_days=ctx.inventory_days,
                    evidence_quality=quality["score"],
                )
            DECISION_SCORES.labels(
                tenant_id=ctx.tenant_id, metric_type="readiness"
            ).set(readiness["readiness_score"])

            GrowthEngine.detect_bottleneck(ctx.ctr, ctx.cr, ctx.frequency)

            # 4. Economic Risk Analysis
            with PIPELINE_STAGE_LATENCY.labels(stage="economic_analysis").time():
                proposed_increase = ctx.spend * ctx.scale_factor
                ev = (
                    (posterior["reconciled_roas"] - 1.0)
                    * proposed_increase
                    * readiness["readiness_score"]
                )

                economics = EconomicEngine.calculate_costs(
                    proposed_increase=proposed_increase,
                    ev=ev,
                    p_success=readiness["readiness_score"],
                    pessimistic_roas=posterior["confidence_interval"][0],
                )
            DECISION_SCORES.labels(
                tenant_id=ctx.tenant_id, metric_type="expected_value"
            ).set(ev)

            # 5. Final Recommendation
            with PIPELINE_STAGE_LATENCY.labels(stage="recommendation_logic").time():
                # Security Layer: If Bayesian math is not stable, downgrade to REDUCE_OR_HOLD
                effective_p_success = (
                    readiness["readiness_score"] if posterior.get("is_stable") else 0.0
                )
                action = RecommendationEngine.determine_action(
                    p_success=effective_p_success,
                    ev=ev,
                    proposed_increase=proposed_increase,
                    safety_buffer=readiness["readiness_score"]
                    if posterior.get("is_stable")
                    else 0.0,
                )
            DECISION_RESULTS.labels(tenant_id=ctx.tenant_id, action=action).inc()

            # 6. Narrative Generation
            with PIPELINE_STAGE_LATENCY.labels(stage="narrative_generation").time():
                return RecommendationEngine.build_defensible_advice(
                    obs=f"Campaign {ctx.campaign_id} analyzed with {ctx.sample_size} orders.",
                    evidence=f"Posterior ROAS: {posterior['reconciled_roas']}x (Interval: {posterior['confidence_interval']})",
                    hypothesis=f"Scaling potential limited by {readiness['bottleneck']}.",
                    quality=quality,
                    readiness=readiness,
                    economics=economics,
                    ev=ev,
                    action=action,
                    reasoning=bot_info["risk_level"],
                    bot_info=bot_info,
                    monthly_spend=ctx.spend * 30,
                    variance_pct=ctx.variance,
                )
        except Exception as e:
            PIPELINE_ERRORS.labels(
                tenant_id=ctx.tenant_id, error_type=type(e).__name__
            ).inc()
            logger.error(
                f"Decision Pipeline failed for {ctx.campaign_id}: {str(e)}",
                exc_info=True,
            )
            raise
