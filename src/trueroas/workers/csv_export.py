import hashlib
import hmac
import csv
import io
import os
from datetime import datetime
from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_path, SessionLocal
from src.trueroas.core.subscriptions import Tenant
from src.trueroas.core.security import derive_tenant_salt
import duckdb
from typing import List, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, Depends
from src.trueroas.core.auth import require_admin, get_current_tenant

def generate_event_id(order_id: str, email: str) -> str:
    """Deterministic event_id for Meta deduplication using application salt."""
    clean_email = (email or "anonymous").lower().strip()
    base = f"{settings.APP_SECRET_SALT}:{order_id}:{clean_email}"
    return hashlib.blake2b(base.encode(), digest_size=16).hexdigest()

async def get_verified_orders_from_db(db_path: str, days: int) -> List[Dict]:
    """Fetch verified reconciliation data from the DuckDB warehouse."""
    with duckdb.connect(db_path, read_only=True) as con:
        rows = con.execute("""
            SELECT order_id, true_revenue, clean_date
            FROM historical_metrics
            WHERE order_id NOT LIKE 'meta_%'
            AND clean_date >= CURRENT_DATE - INTERVAL? DAY
        """, [days]).fetchall()
        return [{"id": r[0], "email": f"order_{r[0]}@trueroas.internal", "total_price": r[1], "currency": "USD", "created_at": r[2].isoformat()} for r in rows]

async def get_detailed_metrics_from_db(db_path: str, days: int) -> List[Dict]:
    """Fetch all detailed performance metrics from the warehouse for deep audit."""
    with duckdb.connect(db_path, read_only=True) as con:
        rows = con.execute("""
            SELECT *
            FROM historical_metrics
            WHERE clean_date >= CURRENT_DATE - INTERVAL? DAY
            ORDER BY clean_date DESC
        """, [days]).fetchall()
        
        # Get column names for CSV header
        columns = [desc[0] for desc in con.description]
        
        return [dict(zip(columns, r)) for r in rows]

def generate_capi_csv(shopify_orders: List[Dict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["event_name","event_time","event_id","value","currency","order_id"])
    for order in shopify_orders:
        event_id = generate_event_id(str(order["id"]), order["email"])
        event_time = int(datetime.fromisoformat(order["created_at"].replace("Z","+00:00")).timestamp())
        writer.writerow(["Purchase", event_time, event_id, order["total_price"], order["currency"], order["id"]])
    return output.getvalue()

def generate_detailed_metrics_csv(metrics: List[Dict]) -> str:
    if not metrics:
        return "status,message\nerror,No data available"
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=metrics[0].keys())
    writer.writeheader()
    writer.writerows(metrics)
    return output.getvalue()

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/api/v1/export/meta-capi-csv")
async def export_meta_csv(
    days: Optional[int] = None, 
    tenant_id: str = Depends(get_current_tenant)
):
    db_path = get_db_path(tenant_id)
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Tenant database not found")
    lookback = days if days is not None else settings.EXPORT_DAYS_LOOKBACK
    orders = await get_verified_orders_from_db(db_path, lookback)
    csv_data = generate_capi_csv(orders)
    return StreamingResponse(io.StringIO(csv_data), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=meta_capi_upload.csv"})

@router.get("/api/v1/export/detailed-audit-csv")
async def export_detailed_metrics(
    days: int = 90, 
    tenant_id: str = Depends(get_current_tenant),
    _ = Depends(require_admin)
):
    """
    Streams audit log using generator pattern to prevent memory exhaustion.
    Calculates SHA-256 checksum for response integrity.
    """
    db_path = get_db_path(tenant_id)
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Tenant database not found")

    # Requirement 4: Fetch tenant-specific HMAC key for digital signature
    central_db = SessionLocal()
    tenant_record = central_db.query(Tenant).filter(Tenant.slug == tenant_id).first()
    if not tenant_record:
        central_db.close()
        raise HTTPException(status_code=404, detail="Tenant metadata not found")
    
    hmac_key = derive_tenant_salt(tenant_record.tenant_secret_salt)
    central_db.close()

    def stream_csv_with_checksum():
        hash_func = hashlib.sha256()
        signature_func = hmac.new(hmac_key, digestmod=hashlib.sha256)
        output = io.StringIO()
        
        query = """
            SELECT decision_id, campaign_id, action, timestamp, expected_roas, actual_roas_90d,
                   ABS(actual_roas_90d - expected_roas) / expected_roas as variance,
                   is_accurate_90d as accuracy_flag
            FROM decision_audit_trail
            WHERE timestamp >= CURRENT_DATE - INTERVAL ? DAY
            ORDER BY timestamp DESC
        """
        
        with duckdb.connect(db_path, read_only=True) as con:
            cursor = con.execute(query, [days])
            cols = [d[0] for d in con.description]
            
            writer = csv.writer(output)
            writer.writerow(cols)
            
            while True:
                chunk = cursor.fetchmany(100)
                if not chunk: break
                writer.writerows(chunk)
                data = output.getvalue()
                encoded_data = data.encode()
                hash_func.update(encoded_data)
                signature_func.update(encoded_data)
                yield data
                output.truncate(0)
                output.seek(0)
            
            # Requirement 3 & 4: Append digital signature to footer for WORM compatibility
            final_sig = signature_func.hexdigest()
            yield f"\n# --- COMPLIANCE SIGNATURE ---\n# SHA-256-HMAC: {final_sig}\n"
            logger.info(f"Compliance Export: Generated signed audit for {tenant_id} (Sig: {final_sig[:12]}...)")
        
    return StreamingResponse(
        stream_csv_with_checksum(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=detailed_audit_{tenant_id}.csv",
            "X-Stream-Active": "true"
        }
    )