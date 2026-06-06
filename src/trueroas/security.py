import hashlib
import hmac
import re
from pathlib import Path

from src.trueroas.core.config import settings
from src.trueroas.core.database import SessionLocal
from src.trueroas.core.subscriptions import SubscriptionService


def sanitize_tenant_id(tenant_id: str) -> str:
    """
    Sanitizes tenant_id to prevent directory traversal and injection.
    Enforces character set [a-zA-Z0-9_-] and a maximum length of 64 characters.
    """
    if not tenant_id:
        return "default"

    # Keep only alphanumeric characters.
    sanitized = re.sub(r"[^a-zA-Z0-9]", "", tenant_id)

    # Enforce max 64 characters and ensure conformant conforming to ^[a-zA-Z0-9_-]+$
    return sanitized[:64] if sanitized else "default"


def derive_tenant_salt(master_secret: str, tenant_id: str) -> bytes:
    """
    Derives a unique per-tenant salt using HMAC-SHA256(master_secret, tenant_id).
    """
    return hmac.new(master_secret.encode(), tenant_id.encode(), hashlib.sha256).digest()


def hash_pii(tenant_id: str, value: str) -> str:
    """
    Hashes Personal Identifiable Information (PII) using BLAKE2b with
    a per-tenant derived key and personalization string.

    The person parameter is limited to the first 16 bytes of the tenant_id.
    """
    if not value:
        return ""

    # Derive per-tenant key from master secret defined in settings
    key = derive_tenant_salt(settings.APP_SECRET_SALT, tenant_id)

    # BLAKE2b 'person' parameter is strictly limited to 16 bytes
    person = tenant_id.encode()[:16]

    return hashlib.blake2b(
        value.strip().lower().encode(), key=key, digest_size=32, person=person
    ).hexdigest()


def validate_path(path: Path) -> Path:
    """
    Ensures that the resolved path is contained within the base data directory.
    """
    base_data_dir = Path(settings.DATA_DIR).resolve()
    resolved_path = Path(path).resolve()

    if not resolved_path.is_relative_to(base_data_dir):
        raise PermissionError(
            f"Security: Path {resolved_path} is outside allowed data directory {base_data_dir}"
        )

    return resolved_path


def suspend_tenant(tenant_id: str):
    """IMMEDIATE mitigation: Suspends a tenant to block API access."""
    db = SessionLocal()
    try:
        SubscriptionService.mark_past_due(db, tenant_id)
        print(f"SUCCESS: Tenant {tenant_id} isolation active (Status: SUSPENDED).")
    except Exception as e:
        print(f"FAILURE: Could not suspend tenant {tenant_id}: {e}")
    finally:
        db.close()
