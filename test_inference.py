import pytest
import math
from src.trueroas.core.inference import DecisionEngine


def test_conjugate_prior_logic_breakdown():
    """
    This test checks the Normal-Normal conjugate prior logic step-by-step.

    Basic formula for Bayesian reconciliation:
    Posterior Mean = (Prior Mean * Prior Precision + Data Mean * Data Precision) / Total Precision
    Precision = 1 / Variance
    """

    # Data:
    meta_roas = 4.0  # Platform reported (Prior)
    true_roas = 2.0  # Business truth (Evidence)
    std_dev = 1.0  # Volatility
    sample_size = 1  # Sample size

    # 1. Prior (Meta):
    # Mean = 4.0, Variance = 1.0 (hardcoded in system)
    # Prior Precision = 1 / 1.0 = 1.0

    # 2. Evidence (True ROAS):
    # Mean = 2.0, Variance = (std_dev^2 / n) = (1.0^2 / 1) = 1.0
    # Evidence Precision = 1 / 1.0 = 1.0

    # 3. Posterior Calculation:
    # Total Precision = 1.0 + 1.0 = 2.0
    # Posterior Mean = (4.0 * 1.0 + 2.0 * 1.0) / 2.0 = 3.0
    # Posterior Variance = 1 / 2.0 = 0.5
    # Posterior Std Dev = sqrt(0.5) ≈ 0.7071

    mean, std = DecisionEngine.calculate_bayesian_posterior(
        meta_roas, true_roas, std_dev, sample_size
    )

    assert mean == pytest.approx(3.0)
    assert std == pytest.approx(math.sqrt(0.5))


def test_evidence_weighting_with_sample_size():
    """
    As sample size increases, the weight (Precision) of the 'Evidence' (real data)
    increases, and the result should converge toward True ROAS.
    """
    meta_roas = 5.0
    true_roas = 2.0
    std_dev = 1.0
    sample_size = 9  # (9 / 1.0^2) = 9.0 precision

    # Prior Precision = 1.0
    # Data Precision = 9.0
    # Posterior Mean = (5.0 * 1.0 + 2.0 * 9.0) / 10.0 = 23 / 10 = 2.3

    mean, _ = DecisionEngine.calculate_bayesian_posterior(
        meta_roas, true_roas, std_dev, sample_size
    )
    assert mean == pytest.approx(2.3)


def test_volatility_impact_on_posterior():
    """
    The higher the volatility (std_dev), the weight (Precision) of the real data
    decreases, and the system's prediction leans more toward the Prior (Meta).
    """
    meta_roas = 4.0
    true_roas = 2.0
    sample_size = 4

    # In low volatility (std_dev = 1.0):
    # Data Precision = 4 / 1^2 = 4.0. Total Precision = 5.0.
    # Mean = (4*1 + 2*4) / 5 = 2.4
    mean_low_vol, _ = DecisionEngine.calculate_bayesian_posterior(
        meta_roas, true_roas, 1.0, sample_size
    )

    # In high volatility (std_dev = 2.0):
    # Data Precision = 4 / 2^2 = 1.0. Total Precision = 2.0.
    # Mean = (4*1 + 2*1) / 2 = 3.0
    mean_high_vol, _ = DecisionEngine.calculate_bayesian_posterior(
        meta_roas, true_roas, 2.0, sample_size
    )

    # In high volatility, the result is closer to Meta's 4.0 (3.0 > 2.4).
    assert mean_high_vol > mean_low_vol
    assert mean_high_vol == pytest.approx(3.0)
    assert mean_low_vol == pytest.approx(2.4)
