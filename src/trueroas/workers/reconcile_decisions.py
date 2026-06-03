import duckdb
import json
from datetime import datetime

def reconcile_past_decisions(db_path: str, tenant_id: str):
    """
    Automated reconciliation at 7, 30, and 90 days.
    Applies variable tolerance based on window maturity.
    """
    with duckdb.connect(db_path) as con:
        # Windows to reconcile: (days_ago, column_suffix, tolerance)
        windows = [
            (7, "7d", 0.35),   # Higher tolerance for partial/lagged data
            (30, "30d", 0.20), # Standard tolerance
            (90, "90d", 0.20)  # Strict threshold for full data
        ]

        for days, suffix, tolerance in windows:
            pending = con.execute(f"""
                SELECT decision_id, expected_roas, timestamp 
                FROM decision_audit_trail 
                WHERE reconciled_{suffix}_at IS NULL 
                AND timestamp <= CURRENT_TIMESTAMP - INTERVAL '{days} days'
            """).fetchall()

            for d_id, expected_roas, decision_ts in pending:
                # Calculate actual ROAS for the specific window
                actual_roas = con.execute("""
                    SELECT SUM(true_revenue) / NULLIF(SUM(normalized_spend), 0)
                    FROM historical_metrics 
                    WHERE clean_date >= ? AND clean_date < ?::DATE + INTERVAL ? DAY
                """, [decision_ts, decision_ts, days]).fetchone()[0] or 0.0

                # Accuracy Check: |actual - expected| / expected < tolerance
                variance = abs(actual_roas - expected_roas) / max(expected_roas, 0.01)
                is_accurate = variance < tolerance

                con.execute(f"""
                    UPDATE decision_audit_trail 
                    SET actual_roas_{suffix} = ?, 
                        is_accurate_{suffix} = ?, 
                        reconciled_{suffix}_at = CURRENT_TIMESTAMP
                    WHERE decision_id = ?
                """, [actual_roas, is_accurate, d_id])