from typing import Optional
from fastapi import APIRouter, Header, status
from pydantic import BaseModel
from src.trueroas.workers.tasks import sync_meta_data

router = APIRouter(prefix="/api/v1", tags=["Sync"])

class SyncRequest(BaseModel):
    tenant_id: Optional[str] = "default"

@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(req: SyncRequest, x_tenant_id: str = Header("default")):
    tenant = req.tenant_id or x_tenant_id
    task = sync_meta_data.delay(tenant)
    return {"task_id": task.id, "status": "queued"}