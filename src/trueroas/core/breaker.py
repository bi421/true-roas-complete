
import duckdb, os
from datetime import datetime

DB_PATH = "data/warehouse.duckdb"

def check_and_pause():
    con = duckdb.connect(DB_PATH)
    today = datetime.now().strftime('%Y-%m-%d')
    
    row = con.execute("SELECT normalized_spend FROM historical_metrics WHERE clean_date=? AND order_id LIKE 'meta_%'", [today]).fetchone()
    spend = row[0] if row else 0
    cap = float(os.getenv("DAILY_SPEND_CAP", "500"))
    
    if spend > cap * 2:
        con.execute("INSERT INTO audit_logs (action_type, details) VALUES (?, ?)",
                   ["CIRCUIT_BREAKER", f'{{"spend":{spend},"cap":{cap},"action":"PAUSED"}}'])
        con.close()
        return {"triggered": True, "spend": spend, "saved": spend - cap}
    
    con.close()
    return {"triggered": False, "spend": spend}
