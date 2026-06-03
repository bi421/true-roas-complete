import asyncio
import logging
from typing import Any, Dict, Optional

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.trueroas.core.config import settings

logger = logging.getLogger("trueroas.email")

# Initialize Resend
resend.api_key = settings.RESEND_API_KEY

# Initialize Jinja2 templates using absolute path from settings
TEMPLATE_DIR = settings.BASE_DIR / "src" / "trueroas" / "templates" / "emails"
_template_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)

class EmailTemplate:
    WELCOME = "welcome"
    PAYMENT_CONFIRMATION = "payment_confirmation"
    PAYMENT_FAILURE = "payment_failure"

async def send_email(
    to: str,
    subject: str,
    html_body: str,
    from_email: Optional[str] = None
) -> Dict[str, Any]:
    if not settings.RESEND_API_KEY:
        logger.warning(f"Resend API Key missing. Skipping email to {to}")
        return {"status": "skipped", "reason": "no_api_key"}

    from_address = from_email or f"TrueROAS <{settings.DEFAULT_FROM_EMAIL}>"
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: resend.Emails.send({
                "from": from_address,
                "to": [to],
                "subject": subject,
                "html": html_body,
            })
        )
        logger.info(f"Email sent to {to}: {subject}")
        return response
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        raise RuntimeError(f"Email delivery failed: {e}")

def render_template(template_id: str, data: Dict[str, Any]) -> str:
    try:
        template = _template_env.get_template(f"{template_id}.html")
        return template.render(**data)
    except Exception as e:
        logger.error(f"Template render failed for {template_id}: {e}")
        return f"<h1>TrueROAS Notification</h1><p>{data.get('message', 'Update for your account.')}</p>"

async def send_payment_confirmation(tenant_id: str, plan_type: str):
    email = f"admin@{tenant_id}.com" # Logic to fetch tenant admin email
    html = render_template(EmailTemplate.PAYMENT_CONFIRMATION, {
        "plan_type": plan_type,
        "dashboard_url": "https://trueroas.com/dashboard"
    })
    await send_email(to=email, subject="Welcome to TrueROAS Accountability", html_body=html)

async def send_payment_failure(tenant_id: str, retry_url: str):
    email = f"admin@{tenant_id}.com" # Logic to fetch tenant admin email
    html = render_template(EmailTemplate.PAYMENT_FAILURE, {
        "retry_url": retry_url
    })
    await send_email(to=email, subject="Action Required: Payment Failed", html_body=html)

def delete_contact(email: str):
    """
    Requirement 3: Hard-delete contact from Resend to fulfill Right to be Forgotten.
    """
    # Note: Resend Python SDK call to suppress/remove contact
    resend.Contacts.remove({"email": email})