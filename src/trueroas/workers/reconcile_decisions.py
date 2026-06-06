import duckdb
from datetime import timedelta


def reconcile_past_decisions(db_path: str, tenant_id: str) -> None:
    """Performs automated reconciliation at 7, 30, and 90-day intervals.

    Applies variable tolerance based on window maturity.

    Args:
        db_path (str): The path to the tenant's DuckDB warehouse.
        tenant_id (str): The unique tenant identifier.
    """
    with duckdb.connect(db_path) as con:
        # Windows to reconcile: (days_ago, column_suffix, tolerance)
        windows = [
            (7, "7d", 0.35),  # Higher tolerance for partial/lagged data
            (30, "30d", 0.20),  # Standard tolerance
            (90, "90d", 0.20),  # Strict threshold for full data
        ]

        for days, suffix, tolerance in windows:
            pending = con.execute(
                f"""
                SELECT decision_id, expected_roas, timestamp 
                FROM decision_audit_trail
                WHERE reconciled_{suffix}_at IS NULL 
                AND timestamp <= CAST(CURRENT_TIMESTAMP AS TIMESTAMP) - INTERVAL {days} DAY
            """
            ).fetchall()

            for d_id, expected_roas, decision_ts in pending:
                window_end = decision_ts + timedelta(days=days)
                # Calculate actual ROAS for the specific window
                res = con.execute(
                    """
                    SELECT SUM(true_revenue) / NULLIF(SUM(normalized_spend), 0)
                    FROM historical_metrics 
                    WHERE clean_date >= ? AND clean_date < ?
                """,
                    [decision_ts, window_end],
                ).fetchone()
                actual_roas = float(res[0]) if res and res[0] is not None else 0.0

                # Accuracy Check: |actual - expected| / expected < tolerance
                expected_roas_safe = max(expected_roas, 0.01)
                variance = abs(actual_roas - expected_roas) / expected_roas_safe
                is_accurate = variance < tolerance

                # Recommendation: Continuous Scoring - shift from binary flags to a ratio
                accuracy_ratio = actual_roas / expected_roas_safe

                con.execute(
                    f"""
                    UPDATE decision_audit_trail 
                    SET actual_roas_{suffix} = ?, 
                        is_accurate_{suffix} = ?, 
                        accuracy_ratio_{suffix} = ?,
                        reconciled_{suffix}_at = CURRENT_TIMESTAMP
                    WHERE decision_id = ?
                """,
                    [actual_roas, is_accurate, accuracy_ratio, d_id],
                )

                # Logic for Systematic Bias calculation for Strategic Memory can be implemented here.
