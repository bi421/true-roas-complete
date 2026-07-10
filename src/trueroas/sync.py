from typing import Optional, Any
from pydantic import BaseModel
from fastapi import APIRouter, Request, status, HTTPException
from celery.result import AsyncResult
from trueroas.core.config import settings
from trueroas.core.limiter import limiter
from trueroas.workers.tasks import celery_app

router = APIRouter(tags=["Data Sync"])


class SyncResponse(BaseModel):
    task_id: str
    status: str
    tenant_id: str


class SyncRequest(BaseModel):
    tenant_id: Optional[str] = "default"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/sync", response_model=SyncResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.RATE_LIMIT_SYNC)  # type: ignore[misc]
async def trigger_sync(request: Request) -> Any:
    """Endpoint deprecated in favor of Zero-Knowledge Client Compute."""
    raise HTTPException(
        status_code=410,
        detail="Endpoint deprecated. Transitioned to Zero-Knowledge architecture.",
    )


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
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
            "tenant": result_data.get("tenant"),
        }

    return {"task_id": task_id, "status": task_result.status}
