import hashlib
import csv
import io
import os
from datetime import datetime
from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_path
import duckdb
from typing import List, Dict

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

def generate_capi_csv(shopify_orders: List[Dict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["event_name","event_time","event_id","value","currency","order_id"])
    for order in shopify_orders:
        event_id = generate_event_id(str(order["id"]), order["email"])
        event_time = int(datetime.fromisoformat(order["created_at"].replace("Z","+00:00")).timestamp())
        writer.writerow(["Purchase", event_time, event_id, order["total_price"], order["currency"], order["id"]])
    return output.getvalue()

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/api/v1/export/meta-capi-csv")
async def export_meta_csv(x_tenant_id: str = Header("default")):
    db_path = get_db_path(x_tenant_id)
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Tenant database not found")
    orders = await get_verified_orders_from_db(db_path, settings.EXPORT_DAYS_LOOKBACK)
    csv_data = generate_capi_csv(orders)
    return StreamingResponse(io.StringIO(csv_data), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=meta_capi_upload.csv"})