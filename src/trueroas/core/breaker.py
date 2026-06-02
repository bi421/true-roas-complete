import duckdb, os
from datetime import datetime
from src.trueroas.core.config import settings

def check_and_pause(db_path: str = None, spend: float = None, cap: float = None, multiplier: float = None):
    """
    Evaluates spend against safety caps.
    Supports direct parameter injection for unit testing and audits.
    """
    current_spend = spend
    current_cap = cap if cap is not None else settings.DAILY_SPEND_CAP
    current_mult = multiplier if multiplier is not None else settings.BREAKER_THRESHOLD_MULTIPLIER

    # If no spend is provided, attempt to fetch from DB
    if current_spend is None and db_path:
        with duckdb.connect(db_path) as con:
            today = datetime.now().strftime('%Y-%m-%d')
            try:
                row = con.execute("SELECT normalized_spend FROM historical_metrics WHERE clean_date=? AND order_id LIKE 'meta_%'", [today]).fetchone()
                current_spend = row[0] if row else 0
            except duckdb.CatalogException:
                return {"triggered": False, "error": "Database tables not initialized", "spend": 0}
    
    # Fallback for safety
    current_spend = current_spend or 0.0

    if current_spend > current_cap * current_mult:
        if db_path and db_path != "TEST":
            with duckdb.connect(db_path) as con:
                con.execute("INSERT INTO audit_logs (action_type, details) VALUES (?, ?)",
                           ["CIRCUIT_BREAKER", f'{{"spend":{current_spend},"cap":{current_cap},"action":"PAUSED"}}'])
        
        return {"triggered": True, "spend": current_spend, "saved": current_spend - current_cap}
    
    return {"triggered": False, "spend": current_spend}
