from typing import Any


class _EmailService:
    def send_nurture_email(
        self, email: str, subject: str, template_id: str, data: dict[str, Any]
    ) -> dict[str, str]:
        return {"status": "skipped"}


email_service = _EmailService()


async def send_payment_confirmation(tenant_id: str, plan_type: str) -> dict[str, str]:
    return {"status": "skipped", "tenant_id": tenant_id, "plan_type": plan_type}


async def send_payment_failure(
    tenant_id: str, retry_url: str | None = None
) -> dict[str, str]:
    response = {"status": "skipped", "tenant_id": tenant_id}
    if retry_url:
        response["retry_url"] = retry_url
    return response
