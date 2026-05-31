import duckdb, os
from datetime import datetime
from src.trueroas.core.config import settings

def check_and_pause(db_path: str):
    # Use context manager to ensure connection closure.
    with duckdb.connect(db_path) as con:
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            row = con.execute("SELECT normalized_spend FROM historical_metrics WHERE clean_date=? AND order_id LIKE 'meta_%'", [today]).fetchone()
            spend = row[0] if row else 0
            
            cap = settings.DAILY_SPEND_CAP
            threshold_multiplier = settings.BREAKER_THRESHOLD_MULTIPLIER
            
            if spend > cap * threshold_multiplier:
                con.execute("INSERT INTO audit_logs (action_type, details) VALUES (?, ?)",
                           ["CIRCUIT_BREAKER", f'{{"spend":{spend},"cap":{cap},"action":"PAUSED"}}'])
                return {"triggered": True, "spend": spend, "saved": spend - cap}
            
            return {"triggered": False, "spend": spend}
        except duckdb.CatalogException:
            return {"triggered": False, "error": "Database tables not initialized", "spend": 0}
