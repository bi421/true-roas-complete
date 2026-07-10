#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import pytest
import uuid
import duckdb
import hmac
import hashlib
import jwt
import warnings
from typing import Generator
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from trueroas.main import app
from trueroas.core.config import settings
from trueroas.core.database import SessionLocal, get_db_path
from trueroas.core.subscriptions import Tenant, SubscriptionTier, TenantStatus
from trueroas.core.migrations import apply_migrations
from trueroas.workers.reconcile_decisions import reconcile_past_decisions

# Suppress the specific deprecation warning about the 'app' shortcut
warnings.filterwarnings(
    "ignore",
    message="The 'app' shortcut is now deprecated",
    category=DeprecationWarning,
    module="httpx._client",
)


def generate_token(tenant_id: str, role: str = "user") -> str:
    payload = {"tenant_id": tenant_id, "role": role, "aud": "trueroas-api"}
    return str(jwt.encode(payload, settings.APP_SECRET_SALT, algorithm="HS256"))


@pytest.fixture(scope="module")
def sandbox_tenant() -> Generator[Tenant, None, None]:
    """Setup a sandbox tenant and run initial migrations."""
    db: Session = SessionLocal()
    tenant_id = f"sandbox_{uuid.uuid4().hex[:6]}"

    tenant = Tenant(
        name="Sandbox Brand",
        slug=tenant_id,
        sqlite_path=get_db_path(tenant_id),
        tenant_secret_salt=uuid.uuid4().hex,
        status=TenantStatus.ACTIVE,
        subscription_tier=SubscriptionTier.PRO,
    )
    db.add(tenant)
    db.commit()

    db_path = get_db_path(tenant_id)
    apply_migrations(db_path)

    yield tenant

    # Cleanup
    db.delete(tenant)
    db.commit()
    db.close()


def test_full_accountability_lifecycle_automated(sandbox_tenant: Tenant) -> None:
    tenant_id = sandbox_tenant.slug
    db_path = get_db_path(tenant_id)
    token = generate_token(tenant_id)
    headers = {"Authorization": f"Bearer {token}"}

    # a) Simulate Shopify: 100 orders ($50K revenue)
    # b) Simulate Meta Ads: 5 campaigns ($20K spend)
    with duckdb.connect(db_path) as con:
        # Seed historical orders
        for i in range(100):
            con.execute(
                "INSERT INTO orders (id, platform, amount, currency, created_at) VALUES (?, 'shopify', 500.0, 'USD', CURRENT_TIMESTAMP - INTERVAL '91 days')",
                [f"order_{i}"],
            )

        # Seed historical metrics (2.5x ROAS baseline)
        for i in range(91, 100):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            con.execute(
                """
                INSERT INTO historical_metrics 
                (account_id, order_id, clean_date, normalized_spend, meta_roas, true_revenue)
                VALUES ('act_sandbox', ?, ?, 2000.0, 3.2, 5000.0)
            """,
                [f"meta_{date}", date],
            )

    # c) User decision: "Scale Campaign A by 30%" (Expected ROAS 3.0)
    decision_id = "dec_scale_camp_a"
    decision_time = datetime.now() - timedelta(days=90)
    with duckdb.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO decision_audit_trail 
            (decision_id, tenant_id, campaign_id, action, timestamp, expected_roas, confidence_level, user_id)
            VALUES (?, ?, 'campaign_A', 'scale', ?, 3.0, 0.85, 'admin_user')
        """,
            [decision_id, tenant_id, decision_time],
        )

    # Simulate outcome data for the 90 days following the decision
    # Meta spends $20k, but Shopify shows $50k (2.5x Real ROAS)
    with duckdb.connect(db_path) as con:
        for i in range(1, 91):
            date = (decision_time + timedelta(days=i)).strftime("%Y-%m-%d")
            con.execute(
                """
                INSERT INTO historical_metrics 
                (account_id, order_id, clean_date, normalized_spend, meta_roas, true_revenue)
                VALUES ('act_sandbox', ?, ?, 222.22, 4.1, 555.55)
            """,
                [f"post_meta_{date}", date],
            )

    # d) 7 Days Later: Verify Decision Accuracy
    # We trigger reconciliation manually to simulate time passage
    reconcile_past_decisions(db_path, tenant_id)

    with TestClient(app) as client:
        resp = client.get("/api/v1/metrics", headers=headers)
        assert resp.status_code == 200
        metrics = resp.json()

        # 7-day variance: |2.5 - 3.0| / 3.0 = 16.6%
        # Threshold for 7d is 35%. Accuracy flag should be True.
        assert metrics["decision_accuracy_7d"] > 0
        print(f"✅ 7-day Accuracy verified: {metrics['decision_accuracy_7d'] * 100}%")

        # e) 30 Days Later: Bayesian reconciliation updated
        # The metrics endpoint in analysis.py returns the pre-cached or computed accuracy
        assert metrics["decision_accuracy_30d"] > 0
    # Risk-adjusted ROAS should be between True (2.5) and Meta (4.1) but leaning toward True due to n=90
    assert 2.4 < metrics["risk_adjusted_roas"] < 3.0
    print(
        f"✅ 30-day Bayesian weight verified. Risk-adjusted ROAS: {metrics['risk_adjusted_roas']}x"
    )

    # f) 90 Days Later: Audit trail CSV export & checksum
    admin_token = generate_token(tenant_id, role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    with TestClient(app) as client:
        export_resp = client.get(
            "/api/v1/export/detailed-audit-csv?days=90", headers=admin_headers
        )
    print("========== RESPONSE DEBUG ==========")
    print("STATUS:", export_resp.status_code)
    print("HEADERS:", dict(export_resp.headers))
    print("CONTENT-TYPE:", export_resp.headers.get("content-type"))
    print("TEXT REPR:", repr(export_resp.text))
    print("CONTENT REPR:", repr(export_resp.content))
    print("JSON PARSEABLE:", end=" ")
    try:
        print(export_resp.json())
    except Exception as e:
        print("NO", repr(e))
    print("====================================")

    assert export_resp.status_code == 200

    content = export_resp.text
    assert "decision_id,campaign_id,action" in content
    assert decision_id in content

    # Verify WORM Compliance Signature
    lines = content.strip().split("\n")
    sig_line = lines[-1]
    assert "SHA-256-HMAC" in sig_line

    # Verify Checksum matching (logic check)
    print("\n===== SIG DEBUG =====")
    print("repr(sig_line):", repr(sig_line))
    print("length:", len(sig_line))
    print("chars:", [ord(c) for c in sig_line])
    print("split result:", sig_line.split(": "))
    print("=====================\n")
    received_sig = sig_line.split(": ")[1]

    # Re-calculate expected signature to prove integrity
    from trueroas.core.security import derive_tenant_salt

    db: Session = SessionLocal()
    tenant_record = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
    assert tenant_record is not None, f"Tenant {tenant_id} not found"
    hmac_key = derive_tenant_salt(tenant_record.tenant_secret_salt)
    db.close()

    csv_body = "\n".join(lines[:-2]) + "\n"
    expected_sig = hmac.new(hmac_key, csv_body.encode(), hashlib.sha256).hexdigest()

    assert received_sig == expected_sig
    print("✅ 90-day Audit Trail verified with digital signature.")

    print("\n🏆 Sandbox E2E Cycle Completed Successfully.")
