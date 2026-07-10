import duckdb

from trueroas.workers.reconcile_decisions import (
    _VALID_SUFFIXES,
    _VALID_DAYS,
    _RECONCILED_AT_COLUMNS,
    _ACTUAL_ROAS_COLUMNS,
    _IS_ACCURATE_COLUMNS,
    _ACCURACY_RATIO_COLUMNS,
    reconcile_past_decisions,
)


def test_reconcile_allowlist_suffixes():
    assert _VALID_SUFFIXES == frozenset(["7d", "30d", "90d"])


def test_reconcile_allowlist_days():
    assert _VALID_DAYS == frozenset([7, 30, 90])


def test_reconcile_column_mappings_complete():
    assert set(_RECONCILED_AT_COLUMNS.keys()) == _VALID_SUFFIXES
    assert set(_ACTUAL_ROAS_COLUMNS.keys()) == _VALID_SUFFIXES
    assert set(_IS_ACCURATE_COLUMNS.keys()) == _VALID_SUFFIXES
    assert set(_ACCURACY_RATIO_COLUMNS.keys()) == _VALID_SUFFIXES

    assert _RECONCILED_AT_COLUMNS["7d"] == "reconciled_7d_at"
    assert _ACTUAL_ROAS_COLUMNS["30d"] == "actual_roas_30d"
    assert _IS_ACCURATE_COLUMNS["90d"] == "is_accurate_90d"
    assert _ACCURACY_RATIO_COLUMNS["7d"] == "accuracy_ratio_7d"


def test_reconcile_column_names_have_no_injection_chars():
    for col in list(_RECONCILED_AT_COLUMNS.values()) + list(_ACTUAL_ROAS_COLUMNS.values()) + \
         list(_IS_ACCURATE_COLUMNS.values()) + list(_ACCURACY_RATIO_COLUMNS.values()):
        assert "'" not in col
        assert ';' not in col
        assert "--" not in col
        assert col.isidentifier()


def test_reconcile_allowlist_rejects_suspicious_strings():
    for malicious in [
        "7d; DROP TABLE--",
        "7d'; DELETE FROM decision_audit_trail; --",
        "7d UNION SELECT * FROM sqlite_master",
        "90d\"; DROP TABLE decision_audit_trail; --",
    ]:
        assert malicious not in _VALID_SUFFIXES
        assert malicious not in _RECONCILED_AT_COLUMNS
        assert malicious not in _ACTUAL_ROAS_COLUMNS
        assert malicious not in _IS_ACCURATE_COLUMNS
        assert malicious not in _ACCURACY_RATIO_COLUMNS


def test_reconcile_hardcoded_windows_use_only_allowlist_values():
    from trueroas.workers.reconcile_decisions import reconcile_past_decisions as rpd
    import inspect

    source = inspect.getsource(rpd)
    windows_line = [line for line in source.splitlines() if "windows =" in line]
    assert windows_line, "Could not find windows list in source"

    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("(") and stripped.endswith("),"):
            parts = stripped.strip("(),").split(",")
            days = int(parts[0].strip())
            suffix = parts[1].strip().strip('"').strip("'")
            assert suffix in _VALID_SUFFIXES, f"Invalid suffix in windows: {suffix}"
            assert days in _VALID_DAYS, f"Invalid days in windows: {days}"


def test_reconcile_valid_suffixes_run_without_sql_error(tmp_path):
    db_path = str(tmp_path / "warehouse.duckdb")
    with duckdb.connect(db_path) as con:
        con.execute("""
            CREATE TABLE decision_audit_trail (
                decision_id TEXT PRIMARY KEY,
                expected_roas REAL,
                timestamp TIMESTAMP,
                reconciled_7d_at TIMESTAMP,
                reconciled_30d_at TIMESTAMP,
                reconciled_90d_at TIMESTAMP,
                actual_roas_7d REAL,
                actual_roas_30d REAL,
                actual_roas_90d REAL,
                is_accurate_7d BOOLEAN,
                is_accurate_30d BOOLEAN,
                is_accurate_90d BOOLEAN,
                accuracy_ratio_7d REAL,
                accuracy_ratio_30d REAL,
                accuracy_ratio_90d REAL
            )
        """)

    reconcile_past_decisions(db_path, tenant_id="test")

    con2 = duckdb.connect(db_path)
    result = con2.execute("SELECT COUNT(*) FROM decision_audit_trail").fetchone()
    con2.close()
    assert result[0] == 0
