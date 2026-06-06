from typing import Any, Dict, List

import duckdb


class DecisionScienceEngine:
    """Calculates model calibration, MAE, and systematic bias."""

    @staticmethod
    def analyze_calibration(db_path: str) -> Dict[str, Any]:
        """
        Analyzes Brier Score and Bias.
        Bias: Sum(Actual - Predicted) / N.
        Negative Bias = Model is over-optimistic.
        """
        with duckdb.connect(db_path, read_only=True) as con:
            metrics = con.execute("""
                SELECT 
                    COUNT(*) as N,
                    AVG(ABS(actual_outcome - predicted_ev)) as mae,
                    AVG(actual_outcome - predicted_ev) as systematic_bias,
                    -- Brier Score for probability calibration
                    AVG(POWER(predicted_confidence - (CASE WHEN is_successful THEN 1 ELSE 0 END), 2)) as brier_score
                FROM decision_audit_trail
                WHERE reconciled_at IS NOT NULL
            """).fetchone()

            if not metrics or metrics[0] == 0:
                return {"status": "insufficient_data"}

            return {
                "sample_size": metrics[0],
                "mean_absolute_error": round(metrics[1], 2),
                "bias_index": round(metrics[2], 2),
                "calibration_brier_score": round(metrics[3], 4),
                "interpretation": (
                    "Over-Optimistic" if metrics[2] < 0 else "Conservative"
                ),
            }

    @staticmethod
    def get_longitudinal_drift(db_path: str) -> List[Dict]:
        """Compares accuracy decay across 7, 30, and 90 day intervals."""
        with duckdb.connect(db_path, read_only=True) as con:
            return con.execute("""
                SELECT 
                    AVG(ABS(outcome_7d - predicted_ev)) as error_7d,
                    AVG(ABS(outcome_30d - predicted_ev)) as error_30d,
                    AVG(ABS(outcome_90d - predicted_ev)) as error_90d
                FROM decision_audit_trail
                WHERE reconciled_90d_at IS NOT NULL
            """).fetchall()
