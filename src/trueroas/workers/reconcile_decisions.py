import duckdb
import shutil
from datetime import timedelta


_VALID_SUFFIXES = frozenset(["7d", "30d", "90d"])
_VALID_DAYS = frozenset([7, 30, 90])
_PG_DUMP_PATH = shutil.which("pg_dump") or "pg_dump"
_SQLITE3_PATH = shutil.which("sqlite3") or "sqlite3"
_RECONCILED_AT_COLUMNS = {
    "7d": "reconciled_7d_at",
    "30d": "reconciled_30d_at",
    "90d": "reconciled_90d_at",
}
_ACTUAL_ROAS_COLUMNS = {
    "7d": "actual_roas_7d",
    "30d": "actual_roas_30d",
    "90d": "actual_roas_90d",
}
_IS_ACCURATE_COLUMNS = {
    "7d": "is_accurate_7d",
    "30d": "is_accurate_30d",
    "90d": "is_accurate_90d",
}
_ACCURACY_RATIO_COLUMNS = {
    "7d": "accuracy_ratio_7d",
    "30d": "accuracy_ratio_30d",
    "90d": "accuracy_ratio_90d",
}


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
            if suffix not in _VALID_SUFFIXES or days not in _VALID_DAYS:
                raise ValueError(
                    f"Invalid reconciliation window: suffix={suffix}, days={days}"
                )

            reconciled_at_col = _RECONCILED_AT_COLUMNS[suffix]
            interval_expr = f"INTERVAL '{days} days'"
            pending = con.execute(
                "SELECT decision_id, expected_roas, timestamp "
                "FROM decision_audit_trail "
                "WHERE " + reconciled_at_col + " IS NULL "
                "AND timestamp <= (CURRENT_TIMESTAMP - " + interval_expr + ")",
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

                actual_roas_col = _ACTUAL_ROAS_COLUMNS[suffix]
                is_accurate_col = _IS_ACCURATE_COLUMNS[suffix]
                accuracy_ratio_col = _ACCURACY_RATIO_COLUMNS[suffix]
                reconciled_at_col = _RECONCILED_AT_COLUMNS[suffix]

                con.execute(
                    "UPDATE decision_audit_trail "
                    "SET " + actual_roas_col + " = ?, "
                    "    " + is_accurate_col + " = ?, "
                    "    " + accuracy_ratio_col + " = ?, "
                    "    " + reconciled_at_col + " = CURRENT_TIMESTAMP "
                    "WHERE decision_id = ?",
                    [actual_roas, is_accurate, accuracy_ratio, d_id],
                )

