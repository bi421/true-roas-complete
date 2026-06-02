import os
from fastapi import FastAPI, Header, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_path
from src.trueroas.workers.csv_export import router as csv_router

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="True ROAS API",
    version="1.0.0",
    description="Shopify + Meta reconciliation API"
)

app.state.limiter = limiter

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(csv_router)

@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."}
    )

@app.get("/health")
async def health():
    return {"status": "ok", "port": settings.APP_PORT}

@app.get("/")
async def root():
    return {"message": "True ROAS API is running", "docs": "/docs"}

@app.post("/api/v1/sync")
@limiter.limit("10/minute")
async def sync_data(request: Request, x_tenant_id: str = Header("default")):
    """
    Sync endpoint - request parameter is required for limiter
    """
    db_path = get_db_path(x_tenant_id)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Initialize DB if needed
    try:
        import duckdb
        with duckdb.connect(db_path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS historical_metrics (
                    order_id VARCHAR PRIMARY KEY,
                    true_revenue DOUBLE,
                    clean_date DATE
                )
            """)
    except Exception as e:
        pass
    
    return {
        "status": "synced",
        "tenant": x_tenant_id,
        "db_path": db_path
    }

@app.get("/api/v1/metrics")
@limiter.limit("30/minute")
async def get_metrics(request: Request, x_tenant_id: str = Header("default")):
    """Get basic metrics"""
    return {
        "tenant": x_tenant_id,
        "true_roas": 0.0,
        "message": "Run sync first to populate data"
    }