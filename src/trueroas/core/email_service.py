import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.trueroas.core.config import settings
from src.trueroas.core.database import SessionLocal

logger = logging.getLogger("trueroas.email")

# Initialize Resend
resend.api_key = settings.RESEND_API_KEY

# Initialize Jinja2 templates using absolute path from settings
TEMPLATE_DIR = settings.BASE_DIR / "src" / "trueroas" / "templates" / "emails"
_template_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailTemplate:
    WELCOME = "welcome"
    PAYMENT_CONFIRMATION = "payment_confirmation"
    PAYMENT_FAILURE = "payment_failure"


def _mask_pii(text: str) -> str:
    """Masks email addresses in a string for log privacy (e.g., u***r@domain.com)."""
    if not text:
        return text

    def mask_match(match):
        email = match.group(0)
        try:
            user, domain = email.split('@', 1)
            if len(user) <= 1:
                return f"*@{domain}"
            return f"{user[0]}***{user[-1]}@{domain}"
        except Exception:
            return "***@***"

    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.sub(email_pattern, mask_match, text)


async def send_email(
    to: str, subject: str, html_body: str, from_email: Optional[str] = None
) -> Dict[str, Any]:
    # 2026 Privacy Standard: Force local sink if STRICT_LOCAL_MODE is enabled
    if settings.STRICT_LOCAL_MODE or not settings.RESEND_API_KEY:
        masked_to = _mask_pii(to)
        masked_body = _mask_pii(html_body)
        logger.info(f"LOCAL_SINK: Strategic advice saved locally for {masked_to}. Egress blocked.")
        log_path = settings.DATA_DIR / "local_emails.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] TO: {masked_to} | SUBJECT: {subject}\n{masked_body}\n{'-'*50}\n")
        return {"status": "local_logged", "path": str(log_path)}

    from_address = from_email or f"{settings.APP_NAME} <{settings.DEFAULT_FROM_EMAIL}>"

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: resend.Emails.send(
                {
                    "from": from_address,
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                }
            ),
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
    from src.trueroas.core.subscriptions import Tenant

    with SessionLocal() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        email = (
            tenant.admin_email
            if tenant and tenant.admin_email
            else f"admin@{tenant_id}.com"
        )

    html = render_template(
        EmailTemplate.PAYMENT_CONFIRMATION,
        {"plan_type": plan_type, "dashboard_url": f"{settings.TRUEROAS_API_URL}/dashboard"},
    )
    await send_email(
        to=email, subject=f"Welcome to {settings.APP_NAME}", html_body=html
    )


async def send_payment_failure(tenant_id: str, retry_url: str):
    from src.trueroas.core.subscriptions import Tenant

    with SessionLocal() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        email = (
            tenant.admin_email
            if tenant and tenant.admin_email
            else f"admin@{tenant_id}.com"
        )

    html = render_template(EmailTemplate.PAYMENT_FAILURE, {"retry_url": retry_url})
    await send_email(
        to=email, subject="Action Required: Payment Failed", html_body=html
    )


def delete_contact(email: str):
    """Hard-deletes a contact from Resend to fulfill the Right to be Forgotten.

    Args:
        email (str): The email address of the contact to remove.
    """
    # Note: Resend Python SDK call to suppress/remove contact
    resend.Contacts.remove({"email": email})
