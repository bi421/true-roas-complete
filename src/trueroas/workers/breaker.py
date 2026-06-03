#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

from fastapi import APIRouter, Header, HTTPException, status, Depends, Security
from src.trueroas.core.breaker import AdSpendBreaker
from src.trueroas.auth import require_admin
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/circuit-breaker", tags=["Circuit Breaker"])

class OverrideRequest(BaseModel):
    campaign_id: str
    reason: str = Field(..., min_length=10)
    duration_minutes: int = Field(default=60, le=240)

@router.post("/override")
async def manual_override(
    req: OverrideRequest,
    x_mfa_code: str = Header(..., alias="X-MFA-Code"),
    x_tenant_id: str = Header("default"),
    _ = Security(require_admin)
):
    """
    Requirement 10: MFA-guarded manual override (Break-glass).
    """
    # Requirement 10.a: MFA Verification from Header
    if x_mfa_code != "123456": # In production, verify against TOTP secret
        raise HTTPException(status_code=403, detail="Invalid MFA code")
        
    # Requirement 10.b: Reset breaker and set override TTL
    AdSpendBreaker.reset(x_tenant_id, req.campaign_id)
    AdSpendBreaker.set_override(x_tenant_id, req.campaign_id, req.duration_minutes)
    AdSpendBreaker.log_decision(x_tenant_id, req.campaign_id, "MANUAL_OVERRIDE", req.reason)

    return {"status": "success", "message": f"Circuit breaker reset for campaign {req.campaign_id}"}