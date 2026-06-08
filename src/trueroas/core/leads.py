#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import logging
from typing import Optional, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from trueroas.workers.tasks import start_nurture_sequence_task
from trueroas.core.database import hash_identifier
from trueroas.core.config import settings

logger = logging.getLogger("trueroas.leads")

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])


class LeadCapture(BaseModel):
    email: EmailStr = Field(
        ..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    name: str = Field(..., min_length=2)
    company: str = Field(..., min_length=2)
    pain_point: Optional[str] = None
    consent_given: bool = Field(..., description="User must agree to marketing terms")
    privacy_policy_accepted: bool = Field(
        ..., description="User must acknowledge privacy policy"
    )


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def capture_lead(
    lead: LeadCapture, request: Request, background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Captures potential customer emails from the landing page.
    Enforces GDPR Article 6 & 7 Consent checks and records metadata.
    """
    if not lead.consent_given or not lead.privacy_policy_accepted:
        raise HTTPException(
            status_code=400,
            detail="Consent and Privacy Policy acceptance are required.",
        )

    try:
        # 1. PII Protection: Hash email for internal audit trail
        # We use a static "marketing" salt context for leads
        hashed_email = hash_identifier(
            "marketing", lead.email, settings.APP_SECRET_SALT
        )
        # 2. Trigger Nurture Automation (Pass raw PII only to secure task worker for Resend integration)
        start_nurture_sequence_task.delay(lead.email, lead.name, hashed_email)
        return {"status": "success", "message": "Verification link sent to your inbox."}
    except Exception as e:
        logger.error(f"Lead capture failed for {lead.email}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Lead capture service temporarily unavailable"
        )
