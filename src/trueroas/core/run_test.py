# mypy: ignore-errors
# TrueROAS - Functional Verification Script
from .market_decision_engine import MarketDecisionEngine


def run_demo():
    print("--- TrueROAS Decision Intelligence - Functional Test ---")

    # Scenario: Meta reports 4.0 ROAS, but reconciled verified ROAS is only 2.2
    result = MarketDecisionEngine.comprehensive_diagnostic(
        platform_reported_roi=4.0,
        actual_verified_roi=2.2,
        sample_size=150,
        volatility=0.25,
        ctr=0.09,
        cvr=0.03,
        current_budget=5000.0,
        vertical="beauty",
    )

    import json

    print(json.dumps(result, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    run_demo()
