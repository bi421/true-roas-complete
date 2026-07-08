import duckdb
from datetime import timedelta


_VALID_SUFFIXES = frozenset(["7d", "30d", "90d"])
_VALID_DAYS = frozenset([7, 30, 90])


def reconcile_past_decisions(db_path: str, tenant_id: str | None = None) -> None:
    """Performs automated reconciliation at 7, 30, and 90-day intervals.

    Uses DuckDB (the tenant warehouse format) instead of sqlite3.

    Applies variable tolerance based on window maturity.

    Args:
        db_path (str): Path to the tenant's DuckDB warehouse.
        tenant_id (str | None): Unused (kept for interface compatibility).
    """

    with duckdb.connect(db_path) as con:
        # Windows to reconcile: (days, column_suffix, tolerance)
        windows = [
            (7, "7d", 0.35),
            (30, "30d", 0.20),
            (90, "90d", 0.20),
        ]

        for days, suffix, tolerance in windows:
            assert suffix in _VALID_SUFFIXES and days in _VALID_DAYS

            pending = con.execute(
                f"""
                SELECT decision_id, expected_roas, timestamp
                FROM decision_audit_trail
                WHERE reconciled_{suffix}_at IS NULL
                  AND timestamp <= (CURRENT_TIMESTAMP - INTERVAL '{days} days')
                """
            ).fetchall()

            for d_id, expected_roas, decision_ts in pending:
                # DuckDB will accept Python datetime objects for parameter binding.
                window_end = decision_ts + timedelta(days=days)

                res = con.execute(
                    """
                    SELECT
                      SUM(true_revenue) / NULLIF(SUM(normalized_spend), 0) AS actual_roas
                    FROM historical_metrics
                    WHERE clean_date >= ? AND clean_date < ?
                    """,
                    [decision_ts, window_end],
                ).fetchone()

                actual_roas = float(res[0]) if res and res[0] is not None else 0.0

                expected_roas_safe = max(float(expected_roas), 0.01)
                variance = abs(actual_roas - expected_roas_safe) / expected_roas_safe
                is_accurate = variance < float(tolerance)
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

