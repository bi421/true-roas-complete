# mypy: ignore-errors
import pytest
from trueroas.security import sanitize_tenant_id, validate_path, hash_pii
from trueroas.core.config import settings


def test_tenant_id_sanitization_and_injection():
    """Ensure injection attempts and traversal characters are stripped."""
    assert sanitize_tenant_id("../../etc/passwd") == "etcpasswd"
    assert sanitize_tenant_id("tenant' OR 1=1--") == "tenantOR11"
    assert sanitize_tenant_id("a" * 100) == "a" * 64  # Max length
    assert sanitize_tenant_id("") == "default"


def test_path_traversal_prevention():
    """Verify validate_path blocks access outside the BASE_DATA_DIR."""
    base_dir = settings.DATA_DIR

    # Valid path
    valid = base_dir / "tenants" / "default" / "warehouse.db"
    assert validate_path(valid) == valid.resolve()

    # Invalid traversal
    invalid = base_dir / ".." / ".." / "etc" / "shadow"
    with pytest.raises(PermissionError, match="Security: Path .* is outside allowed"):
        validate_path(invalid)


def test_hash_collision_and_isolation():
    """Verify deterministic hashing and unique salt per tenant."""
    email = "user@example.com"

    hash1 = hash_pii("tenant_a", email)
    hash2 = hash_pii("tenant_a", email)
    hash_different_tenant = hash_pii("tenant_b", email)

    # Deterministic
    assert hash1 == hash2
    # Isolated (Salted per tenant)
    assert hash1 != hash_different_tenant
    # Secure length (BLAKE2b 32 bytes hex)
    assert len(hash1) == 64
