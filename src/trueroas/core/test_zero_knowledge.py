#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import jwt
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from trueroas.main import app
from trueroas.core.config import settings
from datetime import datetime, timezone

def generate_token(tenant_id: str, role: str = "user") -> str:
    """Generates a test JWT for authentication."""
    payload = {
        "tenant_id": tenant_id,
        "role": role,
        "aud": "trueroas-api",
        "sub": "test-client",
    }
    return jwt.encode(payload, settings.APP_SECRET_SALT, algorithm="HS256")

@patch("httpx.Client")
def test_zk_proof_external_verification_mock(mock_httpx: MagicMock) -> None:
    """
    Test case for verifying the fix for the TypeError when mocking httpx.Client 
    as a context manager.
    """
    # Fix for: TypeError: cannot unpack non-iterable NoneType object
    # Chaining the mock for context manager usage:
    # 1. httpx.Client() -> mock_httpx.return_value
    # 2. __enter__() -> returns the client instance used in 'with'
    # 3. .post(...) -> returns the response mock
    # 4. .json() -> returns the data mock
    mock_httpx.return_value.__enter__.return_value.post.return_value.json.return_value = {
        "verified": True,
        "proof_id": "test-123"
    }
    mock_httpx.return_value.__enter__.return_value.post.return_value.status_code = 200

    with TestClient(app) as client:
        tenant_id = "test-tenant-zk"
        token = generate_token(tenant_id)
        headers = {"X-Tenant-ID": tenant_id, "Authorization": f"Bearer {token}"}

        payload_data = {
            "true_roas": 2.8,
            "meta_roas": 4.2,
            "waste_usd": 480.20,
            "p10_roas": 1.9,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "signature": "valid_signature"
        }

        # Mock security verification and execute request
        with patch("trueroas.main.verify_proof_signature", return_value=True):
            response = client.post("/api/v1/proofs", json=payload_data, headers=headers)
            assert response.status_code == 201