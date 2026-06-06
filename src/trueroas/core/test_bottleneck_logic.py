#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import pytest
from pydantic import ValidationError

from src.trueroas.core.decision_intelligence import GrowthEngine


def test_saturation_only():
    """Must detect ONLY Audience/Saturation."""
    result = GrowthEngine.detect_bottleneck(frequency=5.0, ctr=0.05, cr=0.05)
    assert len(result["issues"]) == 1
    issue = result["issues"][0]
    assert issue["layer"] == "Audience"
    assert issue["issue"] == "Saturation"
    assert issue["priority"] == 1
    assert "evidence_log" in issue
    assert result["primary_issue"] == issue


def test_ctr_only():
    """Must detect ONLY Creative/Attention/CTR."""
    # settings.DEFAULT_BENCHMARK_CTR is 0.015
    result = GrowthEngine.detect_bottleneck(frequency=1.0, ctr=0.005, cr=0.05)
    assert len(result["issues"]) == 1
    issue = result["issues"][0]
    assert issue["layer"] == "Creative"
    assert issue["issue"] == "Attention/CTR"
    assert issue["priority"] == 1
    assert result["primary_issue"] == issue


def test_cr_only():
    """Must detect ONLY Offer/Friction."""
    # settings.DEFAULT_BENCHMARK_CR is 0.025
    result = GrowthEngine.detect_bottleneck(frequency=1.0, ctr=0.05, cr=0.01)
    assert len(result["issues"]) == 1
    issue = result["issues"][0]
    assert issue["layer"] == "Offer"
    assert issue["issue"] == "Friction"
    assert issue["priority"] == 1
    assert result["primary_issue"] == issue


def test_multiple_issues():
    """Must detect ALL THREE issues in a priority-sorted list."""
    result = GrowthEngine.detect_bottleneck(frequency=5.0, ctr=0.005, cr=0.01)
    assert len(result["issues"]) == 3
    layers = [i["layer"] for i in result["issues"]]
    assert "Audience" in layers
    assert "Creative" in layers
    assert "Offer" in layers
    # Verify all are priority 1
    assert all(i["priority"] == 1 for i in result["issues"])
    # Primary issue is the first one detected (Audience in our fixed detection order)
    assert result["primary_issue"]["layer"] == "Audience"


def test_no_issues():
    """Must detect Financial/Capital Efficiency (default) when healthy."""
    result = GrowthEngine.detect_bottleneck(frequency=1.0, ctr=0.05, cr=0.05)
    assert len(result["issues"]) == 1
    issue = result["issues"][0]
    assert issue["layer"] == "Financial"
    assert issue["issue"] == "Capital Efficiency"
    assert issue["priority"] == 2
    assert result["primary_issue"] == issue


def test_threshold_boundary_strict_inequality():
    """Must NOT trigger at exact threshold values (strict inequality check)."""
    avg_f = 2.5
    avg_c = 0.01
    result = GrowthEngine.detect_bottleneck(
        frequency=avg_f, ctr=avg_c, cr=0.05, avg_freq=avg_f, avg_ctr=avg_c
    )
    # Since it's exactly at threshold, it shouldn't trigger Saturation or CTR issues.
    # It should return the default Financial issue.
    assert result["primary_issue"]["layer"] == "Financial"


def test_negative_inputs_validation():
    """Must raise ValidationError via Pydantic for negative values."""
    with pytest.raises(ValidationError):
        GrowthEngine.detect_bottleneck(frequency=-1.0, ctr=0.05, cr=0.05)
    with pytest.raises(ValidationError):
        GrowthEngine.detect_bottleneck(frequency=1.0, ctr=-0.01, cr=0.05)
