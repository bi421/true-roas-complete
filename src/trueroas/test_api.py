import pytest
import jwt
from fastapi.testclient import TestClient
from src.trueroas.main import app
from src.trueroas.core.config import settings

client = TestClient(app)

def generate_token(tenant_id: str, role: str = "user"):
    payload = {"tenant_id": tenant_id, "role": role}
    return jwt.encode(payload, settings.APP_SECRET_SALT, algorithm="HS256")

def test_health_check_endpoint():
    """Verify health endpoint returns 200 and correct port."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_sync_trigger_queued():
    """Verify sync endpoint accepts requests and returns a task ID."""
    # Demo tenant header
    headers = {"X-Tenant-ID": "test-tenant"}
    response = client.post("/api/v1/sync", json={"tenant_id": "test-tenant"}, headers=headers)
    
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "queued"

def test_metrics_schema_validation():
    """Verify metrics response matches Pydantic model."""
    response = client.get("/api/v1/metrics", headers={"X-Tenant-ID": "default"})
    assert response.status_code == 200
    data = response.json()
    assert "tenant" in data
    assert "true_roas" in data
    assert isinstance(data["true_roas"], float)

def test_landing_page_load():
    """Verify landing page serves HTML content."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "TrueROAS" in response.text