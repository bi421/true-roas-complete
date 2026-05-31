
import duckdb, random
from datetime import datetime, timedelta
import os
from src.trueroas.core.config import settings

def sync_shopify(db_path: str):
    """DEMO: generates true revenue 30-40% lower than Meta claims."""
    token = settings.SHOPIFY_TOKEN
    
    # Use context manager to prevent database locks and ensure clean closures.
    with duckdb.connect(db_path) as con:
        rows = con.execute("SELECT clean_date, normalized_spend, meta_roas FROM historical_metrics WHERE order_id LIKE 'meta_%'").fetchall()
        
        for date, spend, meta_roas in rows:
            if not token:  # Demo.
                # True ROAS is 30-40% lower.
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
        
        return {"synced": len(rows)}
