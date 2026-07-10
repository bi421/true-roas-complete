import re
import hmac
import hashlib
import json
import os
import redis
from typing import cast

from pathlib import Path
from datetime import datetime, timezone
from trueroas.core.config import settings


redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def sanitize_tenant_id(tenant_id: str) -> str:
    if not tenant_id:
        return "default"
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", tenant_id)
    return sanitized[:64]


def derive_tenant_salt(tenant_secret_salt: str) -> bytes:
    """Derives a unique per-tenant salt using the master pepper and tenant UUID."""
    return hmac.new(
        settings.APP_SECRET_SALT.encode(), tenant_secret_salt.encode(), hashlib.sha256
    ).digest()


def sign_audit_payload(payload: str, tenant_secret_salt: str) -> str:
    """
    Generates a HMAC-SHA256 signature for audit trail integrity.
    Ensures decisions (like campaign pauses) are verifiable and tamper-proof.
    """
    key = derive_tenant_salt(tenant_secret_salt)
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def verify_audit_signature(
    payload: str, signature: str, tenant_secret_salt: str
) -> bool:
    """Verifies that an audit record has not been tampered with since creation."""
    expected_sig = sign_audit_payload(payload, tenant_secret_salt)
    return hmac.compare_digest(expected_sig, signature)


def hash_pii(tenant_id: str, value: str, tenant_secret_salt: str) -> str:
    """
    Hashes PII with versioned salt to allow for rotation migrations.
    Uses BLAKE2b for speed and keyed hashing.
    Salt Versioning: Managed via SALT_VERSION env variable (GitHub Actions Secret in CI).
    """
    if not value:
        return ""

    version = os.getenv("SALT_VERSION", "v1")
    base_salt = derive_tenant_salt(tenant_secret_salt)
    # Better salt derivation using HMAC for the versioned component
    versioned_salt = hmac.new(base_salt, version.encode(), hashlib.sha256).digest()

    return hashlib.blake2b(
        value.encode(),
        key=versioned_salt,
        digest_size=32,
        person=hashlib.sha256(tenant_id.encode()).digest()[:16],
    ).hexdigest()


def validate_path(path: Path) -> Path:
    """Ensures paths are strictly within the DATA_DIR."""
    try:
        resolved = path.resolve()
        data_root = settings.DATA_DIR.resolve()
        if not resolved.is_relative_to(data_root):
            raise PermissionError(
                f"Security Violation: Path {resolved} is outside {data_root}"
            )
        return resolved
    except Exception:
        raise PermissionError("Security Violation: Invalid path resolution")


def check_rate_limit(tenant_id: str, limit: int = 200, window: int = 3600) -> bool:
    key = f"ratelimit:{tenant_id}"
    with redis_client.pipeline() as pipe:
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        current, _ = pipe.execute()
    return cast(bool, current <= limit)


def verify_proof_signature(
    payload: dict[str, str], signature: str, secret: str
) -> bool:
    """Verifies the HMAC-SHA256 signature of a Zero-Knowledge Strategic Proof.

    The verification is performed against a JSON-serialized representation
    of the payload with keys sorted alphabetically.
    """

    # 1. Replay Attack Prevention: Verify timestamp drift
    # Proof must be submitted within a 5-minute window to be valid.
    timestamp_str: str | None = payload.get("timestamp")

    if not timestamp_str:
        return False

    try:
        proof_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        drift_seconds = abs((now - proof_time).total_seconds())

        if drift_seconds > 300:  # 5 minute TTL
            return False
    except ValueError:
        return False

    # 2. Cryptographic Integrity Check
    # Create a canonical representation of the data (excluding the signature itself).
    # separators=(',', ':') is critical to ensure no whitespace is added, matching cross-platform clients.
    message_data = {k: v for k, v in payload.items() if k != "signature"}
    message = json.dumps(message_data, sort_keys=True, separators=(",", ":")).encode()

    expected_signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected_signature, signature)
