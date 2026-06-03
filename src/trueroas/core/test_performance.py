#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import pytest
import time
from unittest.mock import patch
from src.trueroas.core.inference import DecisionEngine, BayesianInput

def test_posterior_computed_once():
    """Requirement: calculate_bayesian_posterior must be called exactly once per scenario analysis."""
    with patch.object(DecisionEngine, 'calculate_bayesian_posterior', 
                      wraps=DecisionEngine.calculate_bayesian_posterior) as mocked_calc:
        
        # Clear cache to ensure we track the initial call
        DecisionEngine.calculate_bayesian_posterior.cache_clear()

        DecisionEngine.get_full_scenario_analysis(
            current_spend=1000.0,
            current_roas=2.5,
            std_dev=0.5,
            meta_roas=3.0,
            sample_size=100
        )
        
        # Scenario analysis iterates over 5 percentages, but posterior should only be computed once
        assert mocked_calc.call_count == 1

def test_scenario_performance():
    """Requirement: 5 scenarios must complete in < 50ms (CI safety threshold)."""
    start = time.perf_counter()
    
    DecisionEngine.get_full_scenario_analysis(
        current_spend=1000.0,
        current_roas=2.5,
        std_dev=0.5,
        meta_roas=3.0,
        sample_size=100
    )
    
    duration_ms = (time.perf_counter() - start) * 1000
    # Optimized O(1) path usually completes in < 2ms locally.
    assert duration_ms < 50.0

def test_cache_hit():
    """Requirement: Subsequent calls with same inputs must hit the LRU cache."""
    inputs = BayesianInput(
        meta_roas=3.0,
        true_roas=2.5,
        std_dev=0.5,
        sample_size=100
    )
    
    DecisionEngine.calculate_bayesian_posterior.cache_clear()
    
    # First call: Cache miss
    DecisionEngine.calculate_bayesian_posterior(inputs)
    # Second call: Cache hit
    DecisionEngine.calculate_bayesian_posterior(inputs)
    
    info = DecisionEngine.calculate_bayesian_posterior.cache_info()
    assert info.hits == 1
    assert info.misses == 1

def test_big_o_verification():
    """Verification: get_full_scenario_analysis is O(1) relative to data history size."""
    # The method does not accept a list of history, only aggregated primitives (sample_size, std_dev).
    # Therefore, its internal complexity is constant regardless of how many thousands of orders
    # were used to generate those primitives.
    import inspect
    source = inspect.getsource(DecisionEngine.get_full_scenario_analysis)
    
    # The only 'for' loop should be the one iterating over the 5 static scenarios.
    assert source.count("for ") == 1
    assert "percentages =" in source
