from typing import Any, Dict, List

from pydantic import BaseModel


class DecisionIntelligenceSummary(BaseModel):
    recommended_action: str
    reasoning: str
    cost_of_error: float
    cost_of_delay_14d: float
    evidence_quality_score: float
    readiness_score: float
    expected_value: float
    confidence_level: str


class ReasoningOrder(BaseModel):
    observation: str
    evidence: str
    competing_hypotheses: str
    decision_cost: Dict[str, float]
    delay_cost: Dict[str, float]
    evidence_quality: Dict[str, Any]
    decision_readiness: Dict[str, Any]
    what_must_be_true: List[str]
    expected_value: float
    recommendation: str
    validation_plan: str


class IntelligenceResponse(BaseModel):
    summary: DecisionIntelligenceSummary
    reasoning_chain: ReasoningOrder
    raw_metrics: Dict[str, float]
