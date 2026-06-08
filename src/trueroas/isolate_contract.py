import asyncio
import os

# Mock environment to satisfy imports
os.environ["APP_SECRET_SALT"] = "test_salt_32_chars_long_exactly_!!"
os.environ["REDIS_URL"] = "redis://localhost"

from src.trueroas.workers.csv_export import export_detailed_audit_csv
from src.trueroas.core.database import SessionLocal, get_db_path
from src.trueroas.core.subscriptions import Tenant, SubscriptionTier, TenantStatus
from src.trueroas.core.migrations import apply_migrations


async def run_isolation_test() -> None:
    print("MISSION: Call export function directly and verify contract.")

    # 1. Setup minimal DB state for 'default' tenant
    tenant_id = "default"
    db_path = get_db_path(tenant_id)
    apply_migrations(db_path)

    db = SessionLocal()
    if not db.query(Tenant).filter(Tenant.slug == tenant_id).first():
        t = Tenant(
            name="Contract Test",
            slug=tenant_id,
            sqlite_path=db_path,
            tenant_secret_salt="test_tenant_salt",
            status=TenantStatus.ACTIVE,
            subscription_tier=SubscriptionTier.PRO,
        )
        db.add(t)
        db.commit()
    db.close()

    # 2. Call handler directly (Bypassing FastAPI transport)
    print("\n--- Layer 1 & 2: Direct Call ---")
    # Passing dummy values for Depends parameters
    response = await export_detailed_audit_csv(days=7, tenant_id=tenant_id, _=None)

    # Consume generator chunks
    body = ""
    async for chunk in response.body_iterator:
        body += chunk.decode() if isinstance(chunk, bytes) else str(chunk)

    print(f"OUTPUT REPR (first 100): {repr(body[:100])}...")

    lines = body.strip().split("\n")
    last_line = lines[-1]

    if "SHA-256-HMAC" in last_line and not body.startswith('"'):
        print("\nRESULT: PASS (Contract intact at Generator/Response layer)")
    else:
        print("\nRESULT: FAIL (Contract violated)")


if __name__ == "__main__":
    asyncio.run(run_isolation_test())
