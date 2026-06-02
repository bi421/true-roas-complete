import os
import re
import duckdb
from src.trueroas.core.config import settings

# Reach the project root from src/trueroas/core/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def get_db_path(tenant_id: str = "default") -> str:
    """Return sanitized database path for multi-tenant isolation."""
    if not tenant_id or not re.match(r'^[a-z0-9_-]{3,64}$', tenant_id):
        tenant_id = "default"

    tenant_dir = os.path.join(BASE_DIR, "data", "tenants", tenant_id)
    os.makedirs(tenant_dir, exist_ok=True)
    return os.path.join(tenant_dir, "warehouse.duckdb")