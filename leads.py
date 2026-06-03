#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel, EmailStr, Field
from src.trueroas.workers.tasks import start_nurture_sequence_task
from src.trueroas.core.database import hash_identifier
from src.trueroas.core.config import settings
from typing import Optional

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])

class LeadCapture(BaseModel):
    email: EmailStr = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    name: str = Field(..., min_length=2)
    company: str = Field(..., min_length=2)
    pain_point: Optional[str] = None
    consent_given: bool = Field(..., description="User must agree to marketing terms")
    privacy_policy_accepted: bool = Field(..., description="User must acknowledge privacy policy")

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def capture_lead(lead: LeadCapture, request: Request, background_tasks: BackgroundTasks):
    """
    Captures potential customer emails from the landing page.
    Enforces GDPR Article 6 & 7 Consent checks and records metadata.
    """
    if not lead.consent_given or not lead.privacy_policy_accepted:
        raise HTTPException(status_code=400, detail="Consent and Privacy Policy acceptance are required.")

    try:
        if "test" in lead.email.lower():
            # Optional: Filter out junk leads
            return {"status": "ignored", "message": "Test leads are not processed."}

        # 1. PII Protection: Hash email for internal audit trail
        # We use a static "marketing" salt context for leads
        hashed_email = hash_identifier("marketing", lead.email, settings.APP_SECRET_SALT)

        # 2. Trigger Nurture Automation
        # We pass raw PII only to the secure task worker for Resend integration
        start_nurture_sequence_task.delay(lead.email, lead.name, hashed_email)
        
        return {"status": "success", "message": "Verification link sent to your inbox."}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Lead capture service temporarily unavailable")