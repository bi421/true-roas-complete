import time
from fastapi import APIRouter, Header, status
from fastapi.responses import JSONResponse
from celery.result import AsyncResult
from src.trueroas.workers.tasks import celery_app, generate_pdf_report

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])

@router.post("/pdf", status_code=status.HTTP_202_ACCEPTED)
async def generate_audit_report(x_tenant_id: str = Header("default")):
    """
    Queues an async audit report generation.
    """
    # Aggregating data for the background PDF worker
    report_data = {
        "tenant_id": x_tenant_id,
        "timestamp": str(time.time()),
        "summary": {
            "meta_roas": 4.2,
            "true_roas": 2.8,
            "variance": "33%"
        }
    }

    task = generate_pdf_report.delay(x_tenant_id, report_data)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "report_id": task.id,
            "status": "queued",
            "message": "PDF generation started."
        }
    )

@router.get("/{report_id}")
async def get_report_status(report_id: str):
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