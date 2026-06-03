from fastapi import APIRouter, Request, Header
from pydantic import BaseModel
from src.trueroas.core.config import settings
from src.trueroas.core.limiter import limiter

router = APIRouter(prefix="/api/v1", tags=["Analysis"])

class MetricsResponse(BaseModel):
    tenant: str
    true_roas: float
    message: str

@router.get("/metrics", response_model=MetricsResponse)
@limiter.limit(settings.RATE_LIMIT_METRICS)
async def get_metrics(
    request: Request, 
    x_tenant_id: str = Header("default")
) -> MetricsResponse:
    """Get basic performance metrics for the tenant."""
    return MetricsResponse(
        tenant=x_tenant_id,
        true_roas=0.0,
        message="Run sync first to populate data"
    )