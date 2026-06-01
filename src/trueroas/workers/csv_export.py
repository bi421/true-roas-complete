import hashlib
import csv
import io
import os
from datetime import datetime
from src.trueroas.core.config import settings
from typing import List, Dict

def generate_event_id(order_id: str, email: str) -> str:
    """Deterministic event_id for Meta deduplication using application salt."""
    clean_email = (email or "anonymous").lower().strip()
    # Using salt ensures that even with the same email, hashes are unique to this app instance.
    base = f"{settings.APP_SECRET_SALT}:{order_id}:{clean_email}"
    return hashlib.blake2b(base.encode(), digest_size=16).hexdigest()

async def get_shopify_orders(days: int) -> List[Dict]:
    """Fetch recent orders from Shopify (Mock implementation)."""
    # In production, this would use httpx to call the Shopify Admin API.
    return [
        {
            "id": "1001",
            "email": "test1@example.com",
            "total_price": "99.99",
            "currency": "USD",
            "created_at": (datetime.now()).isoformat()
        },
        {
            "id": "1002",
            "email": "test2@example.com",
            "total_price": "149.50",
            "currency": "USD",
            "created_at": (datetime.now()).isoformat()
        }
    ]

def generate_meta_capi_csv(shopify_orders: List[Dict]) -> str:
    """
    Generate CSV for Meta Offline Conversions upload.
    User uploads this manually to Events Manager.
    Columns match Meta spec: https://developers.facebook.com/docs/marketing-api/offline-conversions
    """

    output = io.StringIO()
    writer = csv.writer(output)

    # Meta Offline Events headers.
    writer.writerow([
        "event_name",
        "event_time",
        "event_id",
        "value",
        "currency",
        "order_id"
    ])

    for order in shopify_orders:
        event_id = generate_event_id(str(order["id"]), order["email"])
        event_time = int(datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")).timestamp())

        writer.writerow([
            "Purchase",
            event_time,
            event_id,  # CRITICAL FOR DEDUP.
            order["total_price"],
            order["currency"],
            order["id"]
        ])

    return output.getvalue()

# FastAPI endpoint
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/api/v1/export/meta-capi-csv")
async def export_meta_csv():
    # 1. Fetch Shopify orders from the last 7 days.
    orders = await get_shopify_orders(days=settings.EXPORT_DAYS_LOOKBACK)  # Local helper function.

    # 2. Generate CSV.
    csv_data = generate_meta_capi_csv(orders)

    # 3. Provide as download.
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=meta_capi_upload.csv"}
    )