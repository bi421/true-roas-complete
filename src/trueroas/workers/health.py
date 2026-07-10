from typing import Any

from fastapi import APIRouter

from trueroas.core.config import settings

router = APIRouter(tags=["System"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """
    Health check and basic connectivity status.
    """
    return {"status": "ok", "port": settings.APP_PORT}
