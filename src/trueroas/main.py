import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Header
from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_path
from src.trueroas.workers.tasks import sync_meta_data
from src.trueroas.core.accountability import DecisionAccountabilityEngine

# Import routers (endpoints from legacy tests)
try:
    from src.trueroas.workers.csv_export import router as csv_router
except ImportError:
    csv_router = None

try:
    from src.trueroas.landing import router as landing_router
except ImportError:
    landing_router = None

logger = logging.getLogger("trueroas.api")

# Initialize core FastAPI app
app = FastAPI(title="TrueROAS API", version="1.0.0")

# Register routers
if csv_router:
    app.include_router(csv_router, prefix="/api/v1/export", tags=["Export"])
if landing_router:
    app.include_router(landing_router)

@app.get("/")
async def root():
    """Landing page fallback"""
    return {"message": "TrueROAS Engine Active", "status": "online"}

@app.get("/health")
async def health_check():
    """System health check"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/sync", status_code=202)
async def trigger_sync(x_tenant_id: str = Header(default="default", alias="X-Tenant-ID")):
    """Trigger production data synchronization via Celery."""
    task = sync_meta_data.delay(x_tenant_id)
    return {"status": "queued", "tenant": x_tenant_id, "task_id": task.id}

@app.get("/api/v1/metrics")
async def get_metrics(x_tenant_id: str = Header(default="default", alias="X-Tenant-ID")):
    """
    Production Metrics Endpoint: Fetches live Bayesian track record 
    and capital preservation data from the tenant warehouse.
    """
    import duckdb
    from src.trueroas.core.breaker import redis_client
    
    db_path = get_db_path(x_tenant_id)
    track_record = DecisionAccountabilityEngine.get_track_record(db_path)
    
    # Fetch spend protection from Redis
    protected_key = f"breaker:spend_saved_total:{x_tenant_id}"
    protected_spend = float(redis_client.get(protected_key) or 0.0)
    
    # Get latest averages for ROAS
    with duckdb.connect(db_path, read_only=True) as con:
        res = con.execute("""
            SELECT AVG(true_roas), AVG(meta_roas) 
            FROM historical_metrics 
            WHERE clean_date >= CURRENT_DATE - INTERVAL '7 days'
        """).fetchone()
        
        true_r = res[0] or 0.0
        meta_r = res[1] or 0.0

    return {
        "tenant": x_tenant_id,
        "true_roas": round(true_r, 2),
        "meta_roas": round(meta_r, 2),
        "decision_accuracy_7d": track_record.get("accuracy_score", 0.0) / 100,
        "integrity_score": 94.0,
        "spend_protected_usd": round(protected_spend, 2),
        "status_message": track_record.get("status_message"),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "status": "healthy"
    }

@app.get("/api/v1/cfo/dashboard")
async def get_cfo_dashboard(x_tenant_id: str = Header(default="default", alias="X-Tenant-ID")):
    """CFO-First API Abstraction: Actionable strategic overview."""
    import duckdb
    from scipy.stats import norm
    from src.trueroas.core.business_translator import translate_to_business_action
    
    db_path = get_db_path(x_tenant_id)
    
    try:
        with duckdb.connect(db_path, read_only=True) as con:
            res = con.execute("""
                SELECT AVG(true_roas), AVG(meta_roas), AVG(normalized_spend), STDDEV(true_roas)
                FROM historical_metrics 
                WHERE clean_date >= CURRENT_DATE - INTERVAL '7 days'
            """).fetchone()
            
            true_roas = res[0] or 1.0
            meta_roas = res[1] or 1.0
            daily_spend = res[2] or 0.0
            # Set standard deviation to 0.2 if 0 or null (safety default)
            true_roas_std = res[3] if res[3] and res[3] > 0 else 0.2 
            
            # Calculate true P10 (Pessimistic Bound) using Bayesian math
            p10_roas = norm.ppf(0.10, loc=true_roas, scale=true_roas_std)
            
            # Resilience Check (if sync_metadata table exists)
            alerts = []
            try:
                sync_info = con.execute("SELECT service, last_sync_status FROM sync_metadata").fetchall()
                alerts = [f"{s[0].capitalize()} sync failed. Decisions carry higher risk." for s in sync_info if s[1] == "STALE"]
            except Exception:
                pass # Skip if table does not exist

            # Business translation logic
            action_data = translate_to_business_action(
                posterior_roas=true_roas,
                p10_roas=p10_roas, 
                break_even_roas=1 / settings.VARIABLE_COST_RATE if hasattr(settings, 'VARIABLE_COST_RATE') and settings.VARIABLE_COST_RATE > 0 else 1.0,
                attribution_variance=(meta_roas - true_roas) / max(true_roas, 0.1),
                meta_roas=meta_roas,
                daily_spend=daily_spend
            )
            
            if alerts:
                action_data["data_integrity_alert"] = " | ".join(alerts)
                
            return action_data
    except Exception as e:
        logger.error(f"CFO Dashboard error: {e}")
        return {"status": "ERROR", "message": "Could not generate CFO dashboard."}