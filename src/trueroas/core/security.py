import re
import hmac
import hashlib
from pathlib import Path
from src.trueroas.core.config import settings

def sanitize_tenant_id(tenant_id: str) -> str:
    if not tenant_id:
        return "default"
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', tenant_id)
    return sanitized[:64]

def derive_tenant_salt(tenant_secret_salt: str) -> bytes:
    """Derives a unique per-tenant salt using the master pepper and tenant UUID."""
    return hmac.new(
        settings.APP_SECRET_SALT.encode(),
        tenant_secret_salt.encode(),
        hashlib.sha256
    ).digest()

def hash_pii(tenant_id: str, value: str, tenant_secret_salt: str) -> str:
    if not value: return ""
    salt = derive_tenant_salt(tenant_secret_salt)
    return hashlib.blake2b(
        value.encode(),
        key=salt,
        digest_size=32,
        person=tenant_id.encode()[:16]
    ).hexdigest()

def validate_path(path: Path) -> Path:
    """Ensures paths are strictly within the DATA_DIR."""
    try:
        resolved = path.resolve()
        data_root = settings.DATA_DIR.resolve()
        if not resolved.is_relative_to(data_root):
            raise PermissionError(f"Security Violation: Path {resolved} is outside {data_root}")
        return resolved
    except Exception:
        raise PermissionError("Security Violation: Invalid path resolution")