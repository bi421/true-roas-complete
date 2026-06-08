#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import duckdb
from typing import Any

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel

from trueroas.core.config import settings
from trueroas.core.database import get_db_path
from trueroas.core.limiter import limiter

router = APIRouter(prefix="/api/v1", tags=["Analysis"])


class MetricsResponse(BaseModel):
    tenant: str
    true_roas: float
    meta_roas: float
    variance_pct: float
    message: str


@router.get("/metrics", response_model=MetricsResponse)
@limiter.limit(settings.RATE_LIMIT_METRICS)  # type: ignore[untyped-decorator]
async def get_metrics(
    request: Request, x_tenant_id: str = Header("default")
) -> MetricsResponse:
    """Fetches all consolidated performance metrics from the database."""
    db_path = get_db_path(x_tenant_id)
    with duckdb.connect(db_path, read_only=True) as con:
        res = con.execute("""
            SELECT AVG(true_roas), AVG(meta_roas) 
            FROM historical_metrics 
            WHERE clean_date >= CURRENT_DATE - INTERVAL 7 DAY
        """).fetchone()
        if res is None:
            res = (0.0, 0.0)

        true_r = res[0] or 0.0
        meta_r = res[1] or 0.0
        variance = (meta_r - true_r) / max(true_r, 0.1)

        return MetricsResponse(
            tenant=x_tenant_id,
            true_roas=round(true_r, 2),
            meta_roas=round(meta_r, 2),
            variance_pct=round(variance * 100, 1),
            message="Success",
        )


@router.get("/truth-gap")
async def get_truth_gap_chart_data(
    x_tenant_id: str = Header("default"),
) -> dict[str, Any]:
    """Returns time-series data optimized for chart rendering."""
    db_path = get_db_path(x_tenant_id)
    with duckdb.connect(db_path, read_only=True) as con:
        # Use generate_series to create last 30 days dates and LEFT JOIN
        query = """
            SELECT 
                ds.date_series, 
                COALESCE(hm.meta_roas, 0) as meta_roas, 
                COALESCE(hm.true_roas, 0) as true_roas
            FROM (
                SELECT CAST(range AS DATE) AS date_series 
                FROM generate_series(CURRENT_DATE - INTERVAL 29 DAY, CURRENT_DATE, INTERVAL 1 DAY)
            ) ds
            LEFT JOIN historical_metrics hm ON ds.date_series = hm.clean_date AND hm.order_id LIKE 'meta_%'
            ORDER BY ds.date_series ASC
        """
        rows = con.execute(query).fetchall()

        return {
            "labels": [r[0].strftime("%m-%d") for r in rows],
            "meta_roas": [round(r[1], 2) for r in rows],
            "true_roas": [round(r[2], 2) for r in rows],
        }
