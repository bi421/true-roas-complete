from fastapi import APIRouter

from src.trueroas.core.config import settings

router = APIRouter(tags=["System"])


@router.get("/health")
async def health():
    """
    Health check and basic connectivity status.
    """
    return {"status": "ok", "port": settings.APP_PORT}
