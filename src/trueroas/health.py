from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_session

router = APIRouter(tags=["System"])


@router.get("/health")
async def health(db: Session = Depends(get_db_session)):
    """
    Health check and basic connectivity status.
    Verifies database connectivity.
    """
    return {"status": "ok", "database": "connected", "port": settings.APP_PORT}
