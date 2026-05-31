
import duckdb, random
from datetime import datetime, timedelta
import os

DB_PATH = "data/warehouse.duckdb"

def sync_shopify():
    """DEMO: generates true revenue 30-40% lower than Meta claims"""
    token = os.getenv("SHOPIFY_TOKEN")
    con = duckdb.connect(DB_PATH)
    
    rows = con.execute("SELECT clean_date, normalized_spend, meta_roas FROM historical_metrics WHERE order_id LIKE 'meta_%'").fetchall()
    
    for date, spend, meta_roas in rows:
        if not token:  # demo
            # True ROAS is 30-40% lower
            true_roas = meta_roas * random.uniform(0.6, 0.7)
            true_revenue = spend * true_roas
        else:
            true_revenue = 0
            true_roas = 0
            
        con.execute("""
            UPDATE historical_metrics 
            SET true_revenue=?, true_roas=?, true_cac=?
            WHERE clean_date=? AND order_id LIKE 'meta_%'
        """, [true_revenue, true_roas, spend/max(true_revenue/100,1), date])
    
    con.close()
    return {"synced": len(rows)}
