import logging
import hmac
import hashlib
import base64
import time
import redis
from datetime import datetime
from typing import Any, Dict, Optional

import stripe
from fastapi import APIRouter, Request, Header, status, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_session
from src.trueroas.core.subscriptions import SubscriptionService, PlanType, Subscription, Tenant
from src.trueroas.services.email_service import send_payment_confirmation, send_payment_failure
from src.trueroas.workers.tasks import sync_meta_data

logger = logging.getLogger("trueroas.webhooks")
router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

stripe.api_key = settings.STRIPE_SECRET_KEY
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def check_cb(service: str):
    """Pause processing if failure rate > 5% in 5m window."""
    if redis_client.get(f"cb:active:{service}"):
        raise HTTPException(status_code=503, detail="Webhook processing paused due to high failure rate")

async def update_cb(service: str, success: bool):
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
                logger.critical(f"CIRCUIT BREAKER: {service} paused. Failure rate: {fails/total:.2%}")
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
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error(f"Stripe signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db_session)):
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
            
        return JSONResponse(status_code=200, content={"status": "success"})
    except Exception as e:
        logger.exception(f"Error processing Stripe webhook: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Webhook processing failed")

async def _handle_checkout_completed(db: Session, session: Dict[str, Any]):
    tenant_id = session.get("client_reference_id")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    
    if not tenant_id or not subscription_id:
        logger.error("Missing tenant_id or subscription_id in checkout session")
        return

    stripe_sub = stripe.Subscription.retrieve(subscription_id, expand=["customer"])
    customer = stripe_sub.customer
    price_id = stripe_sub['items']['data'][0]['price']['id']
    plan = PlanType.CORE if price_id == settings.CORE_PLAN_PRICE_ID else PlanType.ACCOUNTABILITY

    SubscriptionService.activate_subscription(
        db=db,
        tenant_id=tenant_id,
        admin_email=customer.email,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        plan_type=plan,
        period_start=datetime.fromtimestamp(stripe_sub.current_period_start),
        period_end=datetime.fromtimestamp(stripe_sub.current_period_end)
    )
    await send_payment_confirmation(tenant_id, plan.value)

async def _handle_payment_succeeded(db: Session, invoice: Dict[str, Any]):
    sub_id = invoice.get("subscription")
    if not sub_id: return
    
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).first()
    if sub:
        stripe_sub = stripe.Subscription.retrieve(sub_id)
        sub.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
        sub.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        sub.status = "active"
        db.commit()

async def _handle_payment_failed(db: Session, invoice: Dict[str, Any]):
    sub_id = invoice.get("subscription")
    sub = SubscriptionService.mark_past_due(db, sub_id)
    if sub:
        await send_payment_failure(sub.tenant_id, retry_url=f"https://trueroas.com/billing")

async def _handle_subscription_deleted(db: Session, subscription: Dict[str, Any]):
    SubscriptionService.cancel_subscription(db, subscription["id"])

@router.post("/shopify")
async def shopify_webhook(
    request: Request,
    x_shopify_topic: str = Header(...),
    x_shopify_shop_domain: str = Header(...),
    x_shopify_hmac_sha256: str = Header(...)
):
    body = await request.body()
    if not verify_shopify_signature(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Unauthorized")

    tenant_id = x_shopify_shop_domain.split('.')[0]
    if x_shopify_topic in ["orders/create", "orders/updated", "refunds/create"]:
        sync_meta_data.delay(tenant_id)
        return {"status": "accepted"}

    return JSONResponse(status_code=200, content={"status": "ignored"})

@router.post("/resend")
async def resend_webhook(request: Request, db: Session = Depends(get_db_session)):
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
            tenant.email_opens += 1
        elif event_type == "email.clicked":
            tenant.email_clicks += 1
        elif event_type == "email.bounced":
            tenant.email_bounces += 1
            logger.warning(f"Email bounce detected. Stats updated for tenant: {tenant.slug}")
        elif event_type == "email.unsubscribed":
            # Resend handles suppression automatically; we log the event
            logger.info(f"Unsubscribe event received for tenant: {tenant.slug}")
        
        db.commit()
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"Resend webhook error: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"error": "Stats update failed"})