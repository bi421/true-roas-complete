import duckdb
from typing import Dict, Any

class DecisionAccountabilityEngine:
    """Tracks the accuracy of past recommendations against actual financial outcomes."""
    
    @staticmethod
    def get_track_record(db_path: str) -> Dict[str, Any]:
        """Calculates the historical accuracy of the decision engine."""
        with duckdb.connect(db_path, read_only=True) as con:
            # Fetch stats for the last 90 days where an outcome has been reconciled
            stats = con.execute("""
                SELECT 
                    COUNT(*) as total_decisions,
                    COUNT(*) FILTER (WHERE is_successful = TRUE) as successful_decisions,
                    AVG(CASE WHEN is_successful = TRUE THEN 1.0 ELSE 0.0 END) * 100 as accuracy_pct,
                    -- Calibration: Predicted Prob vs Actual Outcome
                    AVG(ABS(predicted_confidence - (CASE WHEN is_successful = TRUE THEN 1.0 ELSE 0.0 END))) as cal_err,
                    -- Bias: Mean Forecast Error (Predicted - Actual)
                    AVG(predicted_ev - actual_outcome) as bias,
                    AVG(ABS(actual_outcome - predicted_ev)) as mae
                FROM decision_audit_trail
                WHERE reconciled_at IS NOT NULL 
                AND timestamp >= CURRENT_DATE - INTERVAL '90 days'
            """).fetchone()

            total = stats[0] or 0
            success = stats[1] or 0
            accuracy = round(stats[2], 1) if stats[2] is not None else 0.0
            calibration = round(stats[3], 3) if stats[3] is not None else 0.0
            bias = round(stats[4], 2) if stats[4] is not None else 0.0
            mae = round(stats[5], 2) if stats[5] is not None else 0.0

            # Trend check: Compare last 90 days vs overall
            overall_accuracy = con.execute("""
                SELECT AVG(CASE WHEN is_successful = TRUE THEN 1.0 ELSE 0.0 END) * 100 
                FROM decision_audit_trail 
                WHERE reconciled_at IS NOT NULL
            """).fetchone()[0] or 0.0

            return {
                "accuracy_score": accuracy,
                "total_reconciled": total,
                "success_count": success,
                "historical_benchmark": round(overall_accuracy, 1),
                "systematic_bias": bias,
                "mean_absolute_error": mae,
                "trust_label": "High" if accuracy > 75 else "Stable" if accuracy > 60 else "Learning",
                "status_message": f"Engine has a {accuracy}% accuracy rate based on {total} past scaling outcomes."
            }