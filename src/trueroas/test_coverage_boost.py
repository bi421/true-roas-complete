"""
Coverage boost tests targeting undertested pure-logic modules.
Focuses on: inference, security, subscriptions, drift.
"""

import hashlib
import hmac as _hmac
import json
import math
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from trueroas.core.drift import check_reconciliation_drift
from trueroas.core.inference import (
    BayesianInferenceEngine,
    DecisionEngine,
    BayesianInput,
)
from trueroas.core.security import (
    sanitize_tenant_id,
    sign_audit_payload,
    verify_audit_signature,
    hash_pii,
    verify_proof_signature,
)
from trueroas.core.subscriptions import (
    Tenant,
    TenantStatus,
    SubscriptionTier,
    SubscriptionService,
)

_engine = BayesianInferenceEngine()


# ── inference.py ──────────────────────────────────────────────────────────────


def test_posterior_low_risk() -> None:
    r = _engine.calculate_posterior(3.0, 3.2, 50, 0.5)
    assert r["risk"] == "LOW"
    assert r["is_stable"] is True
    assert math.isfinite(r["reconciled_roas"])


def test_posterior_medium_risk() -> None:
    r = _engine.calculate_posterior(4.0, 2.5, 50, 0.5)
    assert r["risk"] == "MEDIUM"


def test_posterior_critical_risk() -> None:
    r = _engine.calculate_posterior(6.0, 1.0, 50, 0.5)
    assert r["risk"] == "CRITICAL_PLATFORM_FAILURE"


def test_posterior_insufficient_data() -> None:
    r = _engine.calculate_posterior(3.0, 3.0, 5, 0.5)
    assert r["risk"] == "INSUFFICIENT_DATA"
    assert r["reconciled_roas"] == 0.0
    assert r["confidence_interval"] == [0.0, 0.0]


def test_posterior_negative_variance_clamped() -> None:
    r = _engine.calculate_posterior(3.0, 3.0, 20, -1.0)
    assert r["is_stable"] is True


def test_posterior_within_lag_window() -> None:
    r = _engine.calculate_posterior(
        3.0, 3.0, 50, 1.0, platform="meta", days_since_click=10
    )
    assert r["lag_weight"] == 1.0


def test_posterior_google_window() -> None:
    r = _engine.calculate_posterior(
        3.0, 3.0, 50, 1.0, platform="google", days_since_click=50
    )
    assert r["lag_weight"] == 1.0


def test_get_decision_readiness_pause() -> None:
    assert (
        _engine.get_decision_readiness({"reconciled_roas": 1.0})
        == "PAUSE_UNDERPERFORMING"
    )


def test_get_decision_readiness_scale() -> None:
    assert _engine.get_decision_readiness({"reconciled_roas": 2.0}) == "STRONG_SCALE"


def test_simulate_outcomes_basic() -> None:
    r = DecisionEngine.simulate_outcomes(2.0, 0.5)
    assert r["expected_roas"] == 2.0
    assert math.isfinite(r["probability_profit"])


def test_simulate_outcomes_zero_std() -> None:
    r = DecisionEngine.simulate_outcomes(2.0, 0.0)
    assert r["expected_roas"] == 2.0


def test_get_strategic_advice_insufficient() -> None:
    r = DecisionEngine.get_strategic_advice(
        1000, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, {}
    )
    assert r["status"] == "insufficient_data"


def test_get_strategic_advice_strong_scale() -> None:
    r = DecisionEngine.get_strategic_advice(
        500,
        5.0,
        1.0,
        4.0,
        100,
        0.9,
        0.9,
        0.05,
        0.03,
        2.0,
        0.04,
        0.02,
        2.5,
        5000,
        1.0,
        {},
    )
    assert r["action"] == "STRONG_SCALE"


def test_get_strategic_advice_invalid_std() -> None:
    with pytest.raises(ValueError):
        DecisionEngine.get_strategic_advice(
            500,
            2.0,
            0.0,
            4.0,
            100,
            0.9,
            0.9,
            0.05,
            0.03,
            2.0,
            0.04,
            0.02,
            2.5,
            5000,
            1.0,
            {},
        )


def test_update_historical_stats() -> None:
    count, mean, _m2, _decay = DecisionEngine.update_historical_stats(1, 2.0, 0.0, 4.0)
    assert count == 2
    assert mean == pytest.approx(3.0)


def test_bayesian_input_invalid_std() -> None:
    with pytest.raises(ValueError):
        BayesianInput(std_dev=-1.0)


def test_bayesian_input_valid() -> None:
    b = BayesianInput(std_dev=1.0, meta_roas=4.0)
    assert b.std_dev == 1.0


# ── security.py ───────────────────────────────────────────────────────────────


def test_sanitize_tenant_id_strips_special() -> None:
    assert sanitize_tenant_id("tenant!@#123") == "tenant123"


def test_sanitize_tenant_id_empty() -> None:
    assert sanitize_tenant_id("") == "default"


def test_sanitize_tenant_id_truncates() -> None:
    assert len(sanitize_tenant_id("a" * 100)) == 64


def test_sign_and_verify_audit_payload() -> None:
    sig = sign_audit_payload("test_payload", "my_salt")
    assert verify_audit_signature("test_payload", sig, "my_salt") is True


def test_verify_audit_signature_tampered() -> None:
    sig = sign_audit_payload("original", "my_salt")
    assert verify_audit_signature("tampered", sig, "my_salt") is False


def test_hash_pii_empty() -> None:
    assert hash_pii("tenant", "", "salt") == ""


def test_hash_pii_returns_hex() -> None:
    result = hash_pii("tenant", "test@example.com", "salt")
    assert len(result) == 64
    int(result, 16)  # must be valid hex


def test_verify_proof_signature_valid() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    secret = "test_secret"
    payload = {"true_roas": "2.5", "timestamp": ts}
    message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    sig = _hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    payload["signature"] = sig
    assert verify_proof_signature(payload, sig, secret) is True


def test_verify_proof_signature_expired() -> None:
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    assert verify_proof_signature({"timestamp": old_ts}, "sig", "secret") is False


def test_verify_proof_signature_missing_timestamp() -> None:
    assert verify_proof_signature({}, "sig", "secret") is False


def test_verify_proof_signature_bad_timestamp() -> None:
    assert verify_proof_signature({"timestamp": "not-a-date"}, "sig", "secret") is False


# ── subscriptions.py ──────────────────────────────────────────────────────────


def _mock_db() -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = None
    return db


def test_tenant_repr() -> None:
    t = MagicMock(spec=Tenant)
    t.slug = "test"
    t.status = TenantStatus.ACTIVE
    t.subscription_tier = SubscriptionTier.PRO
    assert "test" in Tenant.__repr__(t)


def test_create_subscription_new() -> None:
    db = _mock_db()
    SubscriptionService.create_subscription(db, "new-tenant", SubscriptionTier.PRO)
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_create_subscription_existing_suspended() -> None:
    db = _mock_db()
    existing = MagicMock()
    existing.status = TenantStatus.SUSPENDED
    db.query.return_value.filter.return_value.first.return_value = existing
    SubscriptionService.create_subscription(db, "tenant", SubscriptionTier.PRO)
    db.commit.assert_called_once()


def test_create_subscription_existing_active_raises() -> None:
    db = _mock_db()
    existing = MagicMock()
    existing.status = TenantStatus.ACTIVE
    db.query.return_value.filter.return_value.first.return_value = existing
    with pytest.raises(ValueError):
        SubscriptionService.create_subscription(db, "tenant", SubscriptionTier.PRO)


def test_mark_past_due_not_found_raises() -> None:
    with pytest.raises(ValueError):
        SubscriptionService.mark_past_due(_mock_db(), "missing")


def test_cancel_subscription_not_found_raises() -> None:
    with pytest.raises(ValueError):
        SubscriptionService.cancel_subscription(_mock_db(), "missing")


def test_cancel_subscription_success() -> None:
    db = _mock_db()
    sub = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = sub
    result = SubscriptionService.cancel_subscription(db, "tenant")
    assert result == sub
    assert sub.status == TenantStatus.SUSPENDED


# ── drift.py ──────────────────────────────────────────────────────────────────


def test_drift_empty_data() -> None:
    result = check_reconciliation_drift(MagicMock(empty=True), MagicMock(empty=True))
    assert result is False
