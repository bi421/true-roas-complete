import re
from pathlib import Path
from src.trueroas.core.config import settings

def sanitize_tenant_id(tenant_id: str) -> str:
    if not tenant_id: return "default"
    # Regex ^[a-zA-Z0-9_-]+$
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', tenant_id)
    return sanitized[:64]

def validate_path(path: Path) -> Path:
    resolved = path.resolve()
    data_root = settings.DATA_DIR.resolve()
    if not resolved.is_relative_to(data_root):
        raise PermissionError(f"Security: Blocked access outside data directory: {resolved}")
    return resolved