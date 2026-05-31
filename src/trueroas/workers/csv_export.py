import hashlib
import csv
import io
from datetime import datetime
from typing import List, Dict

def generate_event_id(order_id: str, email: str) -> str:
    """Deterministic event_id for Meta deduplication"""
    base = f"{order_id}:{email.lower().strip()}"
    return hashlib.blake2b(base.encode(), digest_size=16).hexdigest()

def generate_meta_capi_csv(shopify_orders: List[Dict]) -> str:
    """
    Generate CSV for Meta Offline Conversions upload.
    User uploads this manually to Events Manager.
    Columns match Meta spec: https://developers.facebook.com/docs/marketing-api/offline-conversions
    """

    output = io.StringIO()
    writer = csv.writer(output)

    # Meta Offline Events headers
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
            event_id, # CRITICAL FOR DEDUP
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
    # 1. Shopify-аас сүүлийн 7 хоногийн order татах
    orders = await get_shopify_orders(days=7) # Чиний функц

    # 2. CSV үүсгэх
    csv_data = generate_meta_capi_csv(orders)

    # 3. Download болгож өгөх
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=meta_capi_upload.csv"}
    )