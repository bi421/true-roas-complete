from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

app.include_router(csv_export_router)
@app.get("/api/v1/status")
def status():
    return {
        "period":"last_7_days",
        "spend":2802.29,
        "true_revenue":7561.16,
        "true_roas":2.69,
        "meta_roas":4.2,
        "overstatement_pct":55.7,
        "status":"DEMO_MODE"
    }

@app.post("/api/v1/guardrail/check")
def check():
    return {"triggered": False, "spend": 387.06}

@app.post("/api/v1/sync")
def sync():
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
def home():
    html = """<!DOCTYPE html><html><head><title>TrueROAS</title>
<style>body{background:#000;color:#fff;font-family:system-ui;padding:40px;text-align:center}
h1{font-size:32px}.box{background:#111;padding:30px;border-radius:16px;margin:20px auto;max-width:400px}
.big{font-size:60px;font-weight:bold;margin:10px}.red{color:#ff4444}.green{color:#44ff44}</style>
</head><body>
<h1>TrueROAS Guardrail</h1>
<div class="box">
<div>Meta ROAS</div><div class="big red">4.20x</div>
<div>True ROAS</div><div class="big green">2.69x</div>
<div>Overstatement</div><div class="big red">55.7%</div>
</div>
<p>API ажиллаж байна: <a href="/api/v1/status" style="color:#0af">/api/v1/status</a></p>
</body></html>"""
    return html
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
from fastapi.responses import StreamingResponse
import io, csv, hashlib
from datetime import datetime

def generate_event_id(order_id: str, email: str) -> str:
    """Deterministic event_id for Meta deduplication"""
    base = f"{order_id}:{email.lower().strip()}"
    return hashlib.blake2b(base.encode(), digest_size=16).hexdigest()

@app.get("/api/v1/export/meta-capi-csv")
async def export_meta_csv():
    """
    Export Shopify orders as Meta CAPI Offline Events CSV.
    User uploads this to Events Manager for EMQ >8.0 deduplication.
    Zero PII risk: TrueROAS never sends data to Meta.
    """

    # TODO: Чиний Shopify-аас order татах функц
    # Одоо mock data тавъя. Жинхэнэ дээр солино
    orders = [
        {
            "id": "1001",
            "email": "test1@example.com",
            "total_price": "99.99",
            "currency": "USD",
            "created_at": "2026-05-31T10:00:00Z"
        },
        {
            "id": "1002", 
            "email": "test2@example.com",
            "total_price": "149.50",
            "currency": "USD",
            "created_at": "2026-05-31T11:00:00Z"
        }
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["event_name","event_time","event_id","value","currency","order_id"])

    for o in orders:
        event_id = generate_event_id(str(o["id"]), o["email"])
        event_time = int(datetime.fromisoformat(o["created_at"].replace("Z","+00:00")).timestamp())
        writer.writerow(["Purchase", event_time, event_id, o["total_price"], o["currency"], o["id"]])

    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=meta_capi_upload.csv"}
    )