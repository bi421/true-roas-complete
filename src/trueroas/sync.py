from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, Header, status, HTTPException, Depends
from celery.result import AsyncResult
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.trueroas.core.config import settings
from src.trueroas.core.limiter import limiter
from src.trueroas.workers.tasks import sync_meta_data, celery_app
from src.trueroas.core.auth import get_current_tenant
from src.trueroas.core.breaker import redis_client
from src.trueroas.core.database import get_db_session
from src.trueroas.core.subscriptions import Tenant

router = APIRouter(prefix="/api/v1", tags=["Data Sync"])

class SyncResponse(BaseModel):
    task_id: str
    status: str
    tenant_id: str

class SyncRequest(BaseModel):
    tenant_id: Optional[str] = "default"
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@router.post("/sync", response_model=SyncResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.RATE_LIMIT_SYNC)
async def trigger_sync(
    request: Request, 
    sync_req: Optional[SyncRequest] = None,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db_session)
) -> SyncResponse:
    """
    Queues data reconciliation for a specific tenant.
    Enforces 90-day window limit and 5-minute idempotency lock.
    """
    # Verify tenant exists in metadata layer (PostgreSQL) - forces connection pool exercise
    if not db.query(Tenant).filter(Tenant.slug == tenant_id).first():
        raise HTTPException(status_code=404, detail="Tenant metadata not found")

    # 1. Date Range Validation (P0)
    if sync_req and sync_req.start_date and sync_req.end_date:
        start = datetime.fromisoformat(sync_req.start_date)
        end = datetime.fromisoformat(sync_req.end_date)
        if (end - start).days > 90:
            raise HTTPException(status_code=400, detail="Maximum sync range is 90 days")

    # 2. Idempotency Check (5-minute window)
    lock_key = f"sync_lock:{tenant_id}"
    if redis_client.get(lock_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
            detail="Synchronization already in progress for this tenant."
        )
    
    # Set lock with 5-minute TTL
    redis_client.set(lock_key, "1", ex=300)

    start_date = sync_req.start_date if sync_req else None
    end_date = sync_req.end_date if sync_req else None
    request_id = request.state.logger.extra.get("request_id")

    # Trigger task asynchronously via Celery
    task = sync_meta_data.delay(tenant_id, start_date, end_date, request_id=request_id)

    return SyncResponse(
        task_id=task.id,
        status="queued",
        tenant_id=tenant_id
    )

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Polls the status of a specific synchronization task.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    # Production Mapping: Align with Architecture Sequence Diagram
    if task_result.status == "SUCCESS":
        result_data = task_result.result if isinstance(task_result.result, dict) else {}
        return {
            "status": "completed", 
            "records": result_data.get("records", 0),
            "tenant": result_data.get("tenant")
        }
    
    return {"task_id": task_id, "status": task_result.status}