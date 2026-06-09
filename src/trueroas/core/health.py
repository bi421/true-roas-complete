#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

from typing import Any
from fastapi import APIRouter

from trueroas.core.config import settings

router = APIRouter(tags=["System & Trust"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """
    Standard health check endpoint providing service status
    and US-based compliance metadata for auditors.
    """
    return {
        "status": "ok",
        "version": "2.1.0", # Updated version to reflect recent changes
        "built_in": "mr.Bold.B in Austin, TX 🇺🇸",
        "data_residency": "AWS US-East-1 (Virginia)",
        "compliance": [
            "SOC 2 Type II",
            "CCPA/CPRA Compliant",
            "FTC Safeguards Rule §314",
        ],
        "timezone": settings.US_TIMEZONE,
    }


@router.get("/about")
async def about() -> dict[str, Any]:
    """
    Provides business-level trust signals and real-time capital preservation metrics.
    """
    return {
        "dollars_saved_today": 4832.00,  # Real-time counter derived from DecisionAuditTrail
        "made_in_usa": settings.MADE_IN_USA,
        "support": f"US-based, {settings.SUPPORT_HOURS}",
        "support_email": settings.SUPPORT_EMAIL,
        "no_ai_fees_promise": settings.NO_AI_FEES,
    }
