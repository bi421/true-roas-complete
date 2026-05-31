from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

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