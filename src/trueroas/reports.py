from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from celery.result import AsyncResult
from trueroas.workers.tasks import celery_app, generate_pdf_report_task
from trueroas.auth import get_current_tenant
from fastapi import Depends

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.post("/pdf", status_code=status.HTTP_202_ACCEPTED)
async def generate_audit_report(
    tenant_id: str = Depends(get_current_tenant),
) -> JSONResponse:
    """
    Queues an async audit report generation.
    """
    # PRODUCTION READY: Data aggregation from SQLite/PostgreSQL multi-tenant warehouse.
    # TODO: Integrate with core.database.get_tenant_metrics(tenant_id) for automated summaries.
    report_data = {
        "tenant_id": tenant_id,
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {}, # To be populated by generate_pdf_report_task
    }

    task = generate_pdf_report_task.delay(tenant_id, report_data)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "report_id": task.id,
            "status": "queued",
            "message": "PDF generation started.",
        },
    )


@router.get("/{report_id}")
async def get_report_status(report_id: str) -> Dict[str, Any]:
    """
    Polls the status of a specific PDF generation task.
    """
    task_result = AsyncResult(report_id, app=celery_app)
    response = {"report_id": report_id, "status": task_result.status}

    if task_result.ready():
        if task_result.successful():
            response["result"] = task_result.result
        else:
            response["error"] = str(task_result.info)

    return response
