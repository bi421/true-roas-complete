# mypy: ignore-errors
from datetime import datetime, timezone
import hashlib
import hmac
import json
import jwt
from unittest.mock import patch
from fastapi.testclient import TestClient

from trueroas.core.config import settings
from trueroas.main import app


def generate_token(tenant_id: str, role: str = "user") -> str:
    payload = {
        "tenant_id": tenant_id,
        "role": role,
        "aud": "trueroas-api",
        "sub": "test-client",
    }
    return jwt.encode(payload, settings.APP_SECRET_SALT, algorithm="HS256")


def test_health_check_endpoint() -> None:
    """Verify health endpoint returns 200 and correct port."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_sync_trigger_queued():
    """Verify sync endpoint returns 410 Gone as it is deprecated."""
    with TestClient(app) as client:
        token = generate_token("test-tenant")
        headers = {"X-Tenant-ID": "test-tenant", "Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/sync", json={"tenant_id": "test-tenant"}, headers=headers
        )
        assert response.status_code == 410


def test_metrics_schema_validation():
    """Verify metrics response matches Pydantic model."""
    with TestClient(app) as client:
        token = generate_token("default")
        headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": "default"}
        response = client.get("/api/v1/metrics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "tenant" in data
        assert "true_roas" in data
        assert isinstance(data["true_roas"], float)


def test_landing_page_load():
    """Verify landing page serves HTML content."""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        # Accommodate both JSON fallback and HTML landing page
        assert "TrueROAS" in response.text


def test_zk_proof_submission_and_dashboard_retrieval():
    """Verifies end-to-end Zero-Knowledge proof submission and retrieval."""
    with TestClient(app) as client:
        tenant_id = "test-tenant-zk"
        token = generate_token(tenant_id)
        headers = {"X-Tenant-ID": tenant_id, "Authorization": f"Bearer {token}"}

        # 1. Prepare payload with canonical timestamp string
        payload_data = {
            "true_roas": 2.8,
            "meta_roas": 4.2,
            "waste_usd": 480.20,
            "p10_roas": 1.9,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        # 2. Generate HMAC signature mimicking canonical client side logic
        message = json.dumps(
            payload_data, sort_keys=True, separators=(",", ":")
        ).encode()
        signature = hmac.new(
            settings.APP_SECRET_SALT.encode(), message, hashlib.sha256
        ).hexdigest()
        payload_data["signature"] = signature

        # 3. Valid submission
        response = client.post("/api/v1/proofs", json=payload_data, headers=headers)
        assert response.status_code == 201

        # 4. Invalid signature
        tampered_payload = payload_data.copy()
        tampered_payload["signature"] = "invalid_signature"
        response = client.post("/api/v1/proofs", json=tampered_payload, headers=headers)
        assert response.status_code == 403

        # 5. Dashboard verification: verify waste_usd persistence
        response = client.get("/api/v1/cfo/dashboard", headers=headers)
        assert response.status_code == 200
        assert response.json()["waste_usd"] == 480.20


def test_cfo_dashboard_with_learning_active():
    """
    Verifies that the CFO dashboard displays correct learning status and Brier score
    when the self-learning system is enabled and data exists.
    """
    with TestClient(app) as client:
        tenant_id = "test-tenant-learning"
        token = generate_token(tenant_id)
        headers = {"X-Tenant-ID": tenant_id, "Authorization": f"Bearer {token}"}

        # 1. Prepare and submit a valid proof first (required for dashboard processing)
        payload_data = {
            "true_roas": 3.0,
            "meta_roas": 4.5,
            "waste_usd": 250.0,
            "p10_roas": 2.1,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        message = json.dumps(
            payload_data, sort_keys=True, separators=(",", ":")
        ).encode()
        signature = hmac.new(
            settings.APP_SECRET_SALT.encode(), message, hashlib.sha256
        ).hexdigest()
        payload_data["signature"] = signature
        client.post("/api/v1/proofs", json=payload_data, headers=headers)

        # 2. Mock learning module dependencies in main.py to simulate active learning
        with (
            patch("trueroas.main.learning_settings") as mock_settings,
            patch("trueroas.main.PolicyStore") as mock_store_cls,
        ):
            mock_settings.learning_enabled = True
            mock_store_instance = mock_store_cls.return_value
            mock_store_instance.get_latest_policy.return_value = {"brier": 0.18}

            response = client.get("/api/v1/cfo/dashboard", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["learning_status"] == "active"
            assert data["brier_score"] == 0.18


def test_cfo_dashboard_learning_initializing():
    """
    Verifies that the CFO dashboard displays 'initializing' status
    when learning is enabled but no policy data exists yet.
    """
    with TestClient(app) as client:
        tenant_id = "test-tenant-init"
        token = generate_token(tenant_id)
        headers = {"X-Tenant-ID": tenant_id, "Authorization": f"Bearer {token}"}

        # 1. Prepare and submit a valid proof first (required for dashboard processing)
        payload_data = {
            "true_roas": 2.5,
            "meta_roas": 3.5,
            "waste_usd": 100.0,
            "p10_roas": 1.5,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        message = json.dumps(
            payload_data, sort_keys=True, separators=(",", ":")
        ).encode()
        signature = hmac.new(
            settings.APP_SECRET_SALT.encode(), message, hashlib.sha256
        ).hexdigest()
        payload_data["signature"] = signature
        client.post("/api/v1/proofs", json=payload_data, headers=headers)

        # 2. Mock learning module dependencies in main.py to simulate initialization state
        with (
            patch("trueroas.main.learning_settings") as mock_settings,
            patch("trueroas.main.PolicyStore") as mock_store_cls,
        ):
            mock_settings.learning_enabled = True
            mock_store_instance = mock_store_cls.return_value
            # Return None to simulate that no policies exist for this tenant yet
            mock_store_instance.get_latest_policy.return_value = None

            response = client.get("/api/v1/cfo/dashboard", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["learning_status"] == "initializing"
            assert data["brier_score"] is None


def test_cfo_dashboard_learning_db_failure():
    """
    Verifies that the CFO dashboard correctly handles a database failure
    during learning metadata lookup by falling back gracefully.
    """
    with TestClient(app) as client:
        tenant_id = "test-tenant-fail"
        token = generate_token(tenant_id)
        headers = {"X-Tenant-ID": tenant_id, "Authorization": f"Bearer {token}"}

        # 1. Prepare and submit a valid proof first (required for dashboard processing)
        payload_data = {
            "true_roas": 2.0,
            "meta_roas": 3.0,
            "waste_usd": 50.0,
            "p10_roas": 1.2,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        message = json.dumps(
            payload_data, sort_keys=True, separators=(",", ":")
        ).encode()
        signature = hmac.new(
            settings.APP_SECRET_SALT.encode(), message, hashlib.sha256
        ).hexdigest()
        payload_data["signature"] = signature
        client.post("/api/v1/proofs", json=payload_data, headers=headers)

        # 2. Mock learning module dependencies to raise an exception during DB session creation
        with (
            patch("trueroas.main.learning_settings") as mock_settings,
            patch("trueroas.main.SessionLocal") as mock_session,
        ):
            mock_settings.learning_enabled = True
            # Simulate a DB connection error or missing table exception
            mock_session.side_effect = Exception("PostgreSQL Connection Failure")

            response = client.get("/api/v1/cfo/dashboard", headers=headers)

            # The dashboard should still return 200 and the core proof data from DuckDB
            assert response.status_code == 200
            data = response.json()

            # It should have defaulted/remained as "initializing" due to the try-except logic
            assert data["learning_status"] == "initializing"
            assert data["brier_score"] is None

            # Verify core data is still present and correct
            assert data["waste_usd"] == 50.0
            assert data["performance_metrics"]["verified_roas"] == "2.00x"


def test_metrics_learning_integration():
    """Verifies that get_metrics correctly includes learning status metadata."""
    with TestClient(app) as client:
        tenant_id = "test-metrics-learning"
        token = generate_token(tenant_id)
        headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

        # Mock learning module dependencies in main.py
        with (
            patch("trueroas.main.learning_settings") as mock_settings,
            patch("trueroas.main.PolicyStore") as mock_store_cls,
        ):
            mock_settings.learning_enabled = True
            mock_store_instance = mock_store_cls.return_value
            mock_store_instance.get_latest_policy.return_value = {"brier": 0.12}

            response = client.get("/api/v1/metrics", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["learning_status"] == "active"
            assert data["brier_score"] == 0.12
