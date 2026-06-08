from typing import Optional
from fastapi import APIRouter, Header, status, HTTPException
from pydantic import BaseModel

# from trueroas.core.config import settings # Assuming settings might be needed here
router = APIRouter(prefix="/api/v1", tags=["Sync"])


class SyncRequest(BaseModel):
    tenant_id: Optional[str] = "default"


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(req: SyncRequest, x_tenant_id: str = Header("default")) -> None:
    raise HTTPException(
        status_code=410,
        detail="Endpoint deprecated. Transitioned to Zero-Knowledge architecture.",
    )
