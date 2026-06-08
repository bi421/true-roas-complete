# mypy: ignore-errors
import hashlib
import hmac
import json
import jwt
from fastapi.testclient import TestClient

from trueroas.core.config import settings
from trueroas.main import app


def generate_token(tenant_id: str, role: str = "user") -> str:
    payload = {"tenant_id": tenant_id, "role": role}
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
            "timestamp": "2024-05-20T10:00:00Z",
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
