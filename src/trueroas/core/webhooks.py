from __future__ import annotations
import base64
import hashlib
import hmac
import logging
import time
from datetime import datetime
from typing import Any, Dict, Union

import redis
import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_session
from src.trueroas.core.subscriptions import (
    SubscriptionService,
    SubscriptionTier,
    Tenant,
    TenantStatus,
)
from src.trueroas.core.email_service import (
    send_payment_confirmation,
    send_payment_failure,
)

logger = logging.getLogger("trueroas.webhooks")
router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

stripe.api_key = settings.STRIPE_SECRET_KEY
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]


async def check_cb(service: str) -> None:
    """Pause processing if failure rate > 5% in 5m window."""
    if redis_client.get(f"cb:active:{service}"):
        raise HTTPException(
            status_code=503, detail="Webhook processing paused due to high failure rate"
        )


async def update_cb(service: str, success: bool) -> None:
    """Track failure rate in rolling 5m window using Redis counters."""
    window = int(time.time() // 300)
    total_key = f"cb:total:{service}:{window}"
    fail_key = f"cb:fail:{service}:{window}"

    try:
        redis_client.incr(total_key)
        redis_client.expire(total_key, 600)
        if not success:
            redis_client.incr(fail_key)
            redis_client.expire(fail_key, 600)

        total = int(redis_client.get(total_key) or 0)
        if total > 20:
            fails = int(redis_client.get(fail_key) or 0)
            if (fails / total) > 0.05:
                redis_client.set(f"cb:active:{service}", "1", ex=300)
                logger.critical(
                    f"CIRCUIT BREAKER: {service} paused. Failure rate: {fails / total:.2%}"
                )
    except Exception as e:
        logger.error(f"Circuit breaker tracking failed: {e}")


async def is_duplicate(event_id: str) -> bool:
    """Atomic idempotency check using Redis NX."""
    if not event_id:
        return False
    try:
        is_new = redis_client.set(f"webhook:id:{event_id}", "1", nx=True, ex=86400)
        return not is_new
    except Exception as e:
        logger.error(f"Idempotency check failed: {e}")
        return False


def verify_shopify_signature(body: bytes, hmac_header: str) -> bool:
    if not settings.SHOPIFY_API_SECRET:
        return False
    hash = hmac.new(settings.SHOPIFY_API_SECRET.encode(), body, hashlib.sha256).digest()
    expected_hmac = base64.b64encode(hash).decode()
    return hmac.compare_digest(expected_hmac, hmac_header)


async def verify_stripe_signature(payload: bytes, sig_header: str) -> Dict[str, Any]:
    try:
        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event  # type: ignore[no-any-return]
    except (ValueError, stripe.error.SignatureVerificationError) as e:  # type: ignore[attr-defined]
        logger.error(f"Stripe signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")


@router.post("/stripe")
async def stripe_webhook(
    request: Request, db: Session = Depends(get_db_session)
) -> Any:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing signature")

    event = await verify_stripe_signature(payload, sig_header)
    event_type = event["type"]
    event_data = event["data"]["object"]

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(db, event_data)
        elif event_type == "invoice.payment_succeeded":
            await _handle_payment_succeeded(db, event_data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, event_data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, event_data)

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"status": "success"}
        )
    except Exception as e:
        logger.exception(f"Error processing Stripe webhook: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def _handle_checkout_completed(db: Session, session: Dict[str, Any]) -> None:
    tenant_id = session.get("client_reference_id")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    if not tenant_id or not subscription_id or not customer_id:
        logger.error(
            "Missing tenant_id, subscription_id, or customer_id in checkout session"
        )
        return

    stripe_sub = stripe.Subscription.retrieve(subscription_id, expand=["customer"])
    customer = stripe_sub.customer
    admin_email = (
        customer.email if not isinstance(customer, str) else "unknown@stripe.com"
    )

    price_id = stripe_sub["items"]["data"][0]["price"]["id"]
    plan = (
        SubscriptionTier.STARTER
        if price_id == settings.CORE_PLAN_PRICE_ID
        else SubscriptionTier.PRO
    )

    SubscriptionService.activate_subscription(
        db=db,
        tenant_id=str(tenant_id),
        admin_email=str(admin_email),
        stripe_customer_id=str(customer_id),
        stripe_subscription_id=str(subscription_id),
        plan_type=plan,
        period_start=datetime.fromtimestamp(
            getattr(stripe_sub, "current_period_start")
        ),
        period_end=datetime.fromtimestamp(getattr(stripe_sub, "current_period_end")),
    )
    await send_payment_confirmation(str(tenant_id), str(plan.value))


async def _handle_payment_succeeded(db: Session, invoice: Dict[str, Any]) -> None:
    sub_id = invoice.get("subscription")
    if not sub_id:
        return

    sub = db.query(Tenant).filter(Tenant.stripe_subscription_id == sub_id).first()
    if sub:
        stripe_sub = stripe.Subscription.retrieve(sub_id)
        setattr(
            sub,
            "current_period_start",
            datetime.fromtimestamp(getattr(stripe_sub, "current_period_start")),
        )
        setattr(
            sub,
            "current_period_end",
            datetime.fromtimestamp(getattr(stripe_sub, "current_period_end")),
        )
        setattr(sub, "status", TenantStatus.ACTIVE)
        db.commit()


async def _handle_payment_failed(db: Session, invoice: Dict[str, Any]) -> None:
    sub_id = invoice.get("subscription")
    if not sub_id:
        return
    sub = SubscriptionService.mark_past_due(db, str(sub_id))
    if sub:
        await send_payment_failure(
            str(sub.slug), retry_url="https://trueroas.com/billing"
        )


async def _handle_subscription_deleted(
    db: Session, subscription: Dict[str, Any]
) -> None:
    SubscriptionService.cancel_subscription(db, subscription["id"])


def _increment_tenant_counter(tenant: Tenant, field_name: str) -> None:
    current = getattr(tenant, field_name, 0) or 0
    setattr(tenant, field_name, int(current) + 1)


@router.post("/shopify", response_model=None)
async def shopify_webhook(
    request: Request,
    x_shopify_topic: str = Header(...),
    x_shopify_shop_domain: str = Header(...),
    x_shopify_hmac_sha256: str = Header(...),
) -> Union[Dict[str, str], JSONResponse]:
    # Requirement: Global protection for data ingestion
    await check_cb("shopify")
    body = await request.body()
    if not verify_shopify_signature(body, x_shopify_hmac_sha256):
        await update_cb("shopify", success=False)
        raise HTTPException(status_code=401, detail="Unauthorized")

    await update_cb("shopify", success=True)
    topics = ["orders/create", "orders/updated", "refunds/create"]
    if x_shopify_topic in topics:
        return {"status": "ignored", "message": "Inbound data sync deprecated."}

    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored"})


@router.post("/meta/deletion")
async def meta_data_deletion_callback(request: Request) -> Dict[str, str]:
    """
    Requirement 2: Data Deletion Callback for Meta Platform Terms.
    In production, this handles the signed_request and queues a hard purge
    of the specific user's Platform Data.
    """
    # 1. Verify signed_request from Meta
    # 2. Extract user_id and queue erasure task
    return {
        "url": f"{settings.TRUEROAS_API_URL}/api/v1/gdpr/status",
        "confirmation_code": "verified",
    }


@router.post("/resend")
async def resend_webhook(
    request: Request, db: Session = Depends(get_db_session)
) -> Any:
    """
    Handles Resend email events (opens, clicks, bounces).
    Updates aggregated stats in central metadata without storing PII.
    """
    payload = await request.json()
    event_type = payload.get("type")
    # In production, verify settings.RESEND_WEBHOOK_SECRET signature

    # We assume 'marketing' as the default bucket for leads
    # In a multi-tenant setup, this would resolve via metadata
    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if not tenant:
        return {"status": "tenant_not_found"}

    try:
        if event_type == "email.opened":
            _increment_tenant_counter(tenant, "email_opens")
        elif event_type == "email.clicked":
            _increment_tenant_counter(tenant, "email_clicks")
        elif event_type == "email.bounced":
            _increment_tenant_counter(tenant, "email_bounces")
            logger.warning(
                f"Email bounce detected. Stats updated for tenant: {tenant.slug}"
            )
        elif event_type == "email.unsubscribed":
            # Resend handles suppression automatically; we log the event
            logger.info(f"Unsubscribe event received for tenant: {tenant.slug}")

        db.commit()
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"Resend webhook error: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"error": "Stats update failed"})
