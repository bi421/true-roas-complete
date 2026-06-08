#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import pyotp
from fastapi import APIRouter, Depends, Header, HTTPException, Security, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.trueroas.auth import require_admin
from src.trueroas.core.breaker import AdSpendBreaker
from src.trueroas.core.database import get_db_session
from src.trueroas.core.subscriptions import Tenant

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
    db: Session = Depends(get_db_session),
    _: None = Security(require_admin),
) -> dict[str, str]:
    """
    Requirement 10: MFA-guarded manual override (Break-glass).
    """
    # 1. Fetch the tenant's real MFA secret from the database
    tenant = db.query(Tenant).filter(Tenant.slug == x_tenant_id).first()
    if not tenant or not tenant.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not configured for this tenant",
        )

    totp = pyotp.TOTP(str(tenant.mfa_secret))

    if not totp.verify(x_mfa_code):
        raise HTTPException(status_code=403, detail="Invalid MFA code")

    # Requirement 10.b: Reset breaker and set override TTL
    AdSpendBreaker.reset(x_tenant_id, req.campaign_id)
    AdSpendBreaker.set_override(x_tenant_id, req.campaign_id, req.duration_minutes)
    AdSpendBreaker.log_decision(
        x_tenant_id, req.campaign_id, "MANUAL_OVERRIDE", req.reason
    )

    return {
        "status": "success",
        "message": f"Circuit breaker reset for campaign {req.campaign_id}",
    }
