import pytest
from src.trueroas.core.decision_intelligence import RecommendationEngine, GrowthEngine, DecisionThresholds, Severity

def test_recommendation_boundaries():
    """Test precision of action boundaries (e.g., p=0.74 vs 0.75)."""
    config = DecisionThresholds(strong_scale_prob=0.75, strong_scale_ev_pct=0.5)
    
    # Boundary: Just below threshold
    action_fail = RecommendationEngine.determine_action(
        p_success=0.74, ev=600, proposed_increase=1000, safety_buffer=0.5, config=config
    )
    assert action_fail == "CAUTIOUS_SCALE"

    # Boundary: Exactly at/above threshold
    action_pass = RecommendationEngine.determine_action(
        p_success=0.751, ev=600, proposed_increase=1000, safety_buffer=0.5, config=config
    )
    assert action_pass == "STRONG_SCALE"

    # EV Threshold Check: EV must be > 50% of proposed increase for STRONG_SCALE
    action_ev_fail = RecommendationEngine.determine_action(
        p_success=0.9, ev=400, proposed_increase=1000, safety_buffer=0.5, config=config
    )
    assert action_ev_fail == "CAUTIOUS_SCALE"

def test_multi_bottleneck_detection():
    """Verify multiple constraints are detected and prioritized correctly."""
    # Scenarios: High frequency (Saturation) and Low CTR (Creative)
    result = GrowthEngine.detect_bottleneck(
        ctr=0.005, # Very Low
        cr=0.03,   # Healthy
        frequency=4.5, # Critical
        avg_ctr=0.015,
        avg_freq=2.5
    )
    
    issues = [i.issue for i in result.issues]
    assert "Saturation" in issues
    assert "Attention/CTR" in issues
    # Saturation has a higher impact_score (0.8) in logic than CTR (0.7)
    assert result.primary_issue.issue == "Saturation"

def test_no_bottleneck_health():
    """Verify clean health when all metrics exceed benchmarks."""
    result = GrowthEngine.detect_bottleneck(ctr=0.03, cr=0.05, frequency=1.5)
    assert len(result.issues) == 0
    assert any(log.label == "Funnel Health" for log in result.evidence_log)