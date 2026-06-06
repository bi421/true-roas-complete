# Contributing to TrueROAS

Thank you for your interest in contributing to TrueROAS! To maintain the high precision and production-grade quality of this platform, please follow these guidelines.

## Code Style

We enforce strict code quality standards to ensure maintainability and readability:
- **Formatting:** All code should be formatted using `black`.
- **Import Sorting:** Use `isort` to keep imports organized.
- **Type Checking:** We use `mypy --strict` for static type analysis.

## Testing Requirements

TrueROAS is a mission-critical financial audit tool. Every Pull Request must:
1. Pass the full test suite: `pytest`
2. Pass the property-based math invariant tests: `pytest tests/property/`
3. Pass the Market Decision Engine logic tests: `pytest src/trueroas/core/test_market_decision_engine.py`
4. Pass strict type checking: `mypy --strict src/`
5. Include new tests for any added features or fixed bugs.

## Commit Message Format

We use structured commit messages to maintain a clear and automated changelog:
- `feat:` for new features.
- `fix:` for bug fixes.
- `refactor:` for code restructuring without changing behavior.
- `test:` for adding or updating tests.
- `math:` for changes to statistical models or decision thresholds.

## Decision Threshold Changes

TrueROAS is built on deterministic statistical models. Any changes to decision thresholds (e.g., `STRONG_SCALE_PROB_THRESHOLD`) **must** include backtesting evidence in the PR description. You must demonstrate how the change affects Decision Accuracy Scores and capital drawdown across historical multi-tenant datasets.

**Precision over vanity. Evidence over assumptions. Decisions over dashboards.**