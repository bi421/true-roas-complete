import os
import uuid
import logging
import time
from contextlib import asynccontextmanager
import redis
from typing import Optional
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import OperationalError
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST, Response

from src.trueroas.core.config import settings
from src.trueroas.api.routes import health, sync, analysis, reports, leads, breaker, gdpr
from src.trueroas.workers.csv_export import router as csv_router
from src.trueroas.workers.webhooks import router as unified_webhook_router
from src.trueroas.core.migrations import apply_migrations
from src.trueroas.core.database import engine, get_db_path
from src.trueroas.core.subscriptions import Base
from src.trueroas.core.limiter import limiter
from src.trueroas.landing import router as landing_router

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint", "method", "status"]
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", 
    "Total HTTP requests processed", 
    ["status", "endpoint", "method", "tenant_id"]
)

def setup_logging():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s',
        rename_fields={"asctime": "timestamp", "levelname": "level"}
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

setup_logging()
logger = logging.getLogger("trueroas.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure data directories and base migrations are applied
    logger.info("Initializing TrueROAS Production Server...")
    os.makedirs(os.path.join(settings.BASE_DIR, "data", "tenants"), exist_ok=True)
    # Initialize Central Subscription DB
    Base.metadata.create_all(bind=engine)
    # Pre-initialize default tenant for health checks
    apply_migrations(get_db_path("default"))
    yield
    # Shutdown: Clean up resources if any
    logger.info("Shutting down TrueROAS Server...")

app = FastAPI(
    title="True ROAS API",
    version="1.0.0",
    description="Shopify + Meta reconciliation API",
    lifespan=lifespan
)

app.state.limiter = limiter

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://trueroas.com",
        "https://app.trueroas.com",
        "http://localhost:3000" # Local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(csv_router)
app.include_router(landing_router)
app.include_router(health.router)
app.include_router(sync.router)
app.include_router(analysis.router)
app.include_router(reports.router)
app.include_router(unified_webhook_router)
app.include_router(leads.router)
app.include_router(breaker.router)
app.include_router(gdpr.router)

@app.get("/metrics")
async def metrics():
    """Exposes Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Tracing Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # Requirement: Maintenance Mode implementation
    if settings.MAINTENANCE_MODE and request.url.path not in ["/health", "/metrics"]:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "System is undergoing scheduled maintenance. Please check Slack for updates."}
        )

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    tenant_id = request.headers.get("X-Tenant-ID", "unknown")
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Enhanced structured logging context
    struct_logger = logging.LoggerAdapter(logger, {"request_id": request_id, "tenant_id": tenant_id})
    request.state.logger = struct_logger
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    duration_ms = duration * 1000

    # Update Prometheus metrics
    HTTP_REQUESTS_TOTAL.labels(
        status=response.status_code,
        endpoint=request.url.path,
        method=request.method,
        tenant_id=tenant_id
    ).inc()
    
    HTTP_REQUEST_DURATION.labels(
        endpoint=request.url.path,
        method=request.method,
        status=response.status_code
    ).observe(duration)

    # Structured log output for production observability
    struct_logger.info(f"{request.method} {request.url.path} - {response.status_code}", extra={
        "duration_ms": round(duration_ms, 2),
        "user_agent": user_agent
    })
    
    response.headers["X-Process-Time"] = str(duration)
    response.headers["X-Request-ID"] = request_id
    return response

# Global Exception Handlers
@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request parameters.", "errors": exc.errors()}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log only the error type and message, avoiding full exc_info in production logs 
    # to prevent accidental secret leakage from local stack variables.
    error_id = uuid.uuid4()
    logger.critical(f"Unhandled System Error [{error_id}]: {exc.__class__.__name__}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An internal server error occurred. Reference: {error_id}"}
    )