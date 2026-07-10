from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from trueroas.core.config import settings
from trueroas.core.database import get_db_session

router = APIRouter(tags=["System"])


@router.get("/health")
async def health(db: Session = Depends(get_db_session)) -> dict[str, Any]:
    """
    Health check and basic connectivity status.
    Verifies database connectivity.
    """
    try:
        # Perform a minimal query to verify DB connectivity
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "port": settings.APP_PORT}
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Database connection failed: {str(e)}"
        )
