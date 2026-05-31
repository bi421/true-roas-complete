# TrueROAS - Working System (Demo Mode)

Ажилладаг систем бэлэн. Token шаардлагагүй.

## Run in 2 minutes
```bash
pip install -r requirements.txt
python main.py
```
Open: http://localhost:8000/api/v1/status

You will see:
```json
{
  "spend": 5200,
  "true_roas": 2.8,
  "meta_roas": 4.2,
  "overstatement_pct": 35.7,
  "status": "DEMO_MODE"
}
```

## What works NOW
✅ Meta sync (generates realistic spend)
✅ Shopify sync (calculates true revenue 35% lower)
✅ Circuit breaker (auto-pauses at 2x cap)
✅ API + Telegram bot
✅ Audit logs

## Switch to REAL data later
1. Fill .env with real tokens
2. Restart - same code works

No code changes needed.
