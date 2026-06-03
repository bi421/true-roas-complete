#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import logging
import hmac
import hashlib
import base64
import time
import redis
from contextlib import closing
from datetime import datetime
from typing import Any, Dict, Optional

import stripe
from fastapi import APIRouter, Request, Header, status, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_session
from src.trueroas.core.subscriptions import SubscriptionService, Subscription, SubscriptionStatus, SubscriptionTier
from src.trueroas.services.email_service import send_payment_confirmation, send_payment_failure
from src.trueroas.workers.tasks import sync_meta_data

logger = logging.getLogger("trueroas.webhooks")
router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

def verify_shopify_signature(body: bytes, hmac_header: str) -> bool:
    """
    Verifies the HMAC signature from Shopify to ensure request authenticity.
    """
    if not settings.SHOPIFY_API_SECRET:
        return False
    hash = hmac.new(settings.SHOPIFY_API_SECRET.encode(), body, hashlib.sha256).digest()
    expected_hmac = base64.b64encode(hash).decode()
    return hmac.compare_digest(expected_hmac, hmac_header)

async def verify_stripe_signature(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """
    Verify Stripe webhook signature.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError as e:
        logger.error(f"Invalid Stripe payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid Stripe signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

@router.post("/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events for subscription management.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        logger.error("Missing stripe-signature header")
        raise HTTPException(status_code=400, detail="Missing signature")

    event = await verify_stripe_signature(payload, sig_header)
    event_type = event["type"]
    event_data = event["data"]["object"]

    logger.info(f"Processing Stripe event: {event_type}")

    with closing(next(get_db_session())) as db:
        try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(db, event_data)
        elif event_type == "invoice.payment_succeeded":
            await _handle_payment_succeeded(db, event_data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, event_data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, event_data)
        else:
            logger.info(f"Ignoring unhandled event type: {event_type}")

        return {"status": "success", "event_id": event["id"]}
    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")

async def _handle_checkout_completed(db: Session, session: Dict[str, Any]):
    """Activate subscription after successful checkout."""
    tenant_id = session.get("client_reference_id")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    
    if not tenant_id:
        logger.error("Missing client_reference_id in checkout session")
        raise ValueError("Missing tenant_id")
    
    stripe_sub = stripe.Subscription.retrieve(subscription_id, expand=["customer"])
    customer = stripe_sub.customer
    price_id = stripe_sub['items']['data'][0]['price']['id']
    plan = SubscriptionTier.CORE if price_id == settings.CORE_PLAN_PRICE_ID else SubscriptionTier.ACCOUNTABILITY

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
    await send_payment_confirmation(tenant_id, plan_type=plan.value)
    logger.info(f"Activated subscription for tenant {tenant_id}")

async def _handle_payment_succeeded(db: Session, invoice: Dict[str, Any]):
    """Renew subscription after successful payment."""
    subscription_id = invoice.get("subscription")
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == subscription_id).first()
    if sub:
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        sub.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
        sub.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        sub.status = SubscriptionStatus.ACTIVE
        db.commit()
        logger.info(f"Renewed subscription for tenant {sub.tenant_id}")

async def _handle_payment_failed(db: Session, invoice: Dict[str, Any]):
    """Mark subscription past due after failed payment."""
    subscription_id = invoice.get("subscription")
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == subscription_id).first()
    if sub:
        SubscriptionService.mark_past_due(db, sub.tenant_id)
        await send_payment_failure(sub.tenant_id, retry_url=f"/billing/retry?tenant={sub.tenant_id}")
        logger.warning(f"Marked subscription past due for tenant {sub.tenant_id}")

async def _handle_subscription_deleted(db: Session, subscription: Dict[str, Any]):
    """Cancel subscription when deleted in Stripe."""
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == subscription["id"]).first()
    if sub:
        SubscriptionService.cancel_subscription(db, sub.tenant_id)
        logger.info(f"Canceled subscription for tenant {sub.tenant_id}")

@router.post("/shopify")
async def shopify_webhook(
    request: Request,
    x_shopify_topic: str = Header(...),
    x_shopify_shop_domain: str = Header(...),
    x_shopify_hmac_sha256: str = Header(...)
):
    body = await request.body()
    if not verify_shopify_signature(body, x_shopify_hmac_sha256):
        logger.warning(f"Unauthorized Shopify Webhook attempt from {x_shopify_shop_domain}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    tenant_id = x_shopify_shop_domain.split('.')[0]
    payload = await request.json()
    
    if x_shopify_topic in ["orders/create", "orders/updated", "refunds/create"]:
        # Requirement: Observability matching SRE log patterns (grep "shopify_webhook")
        logger.info(
            f"Shopify webhook {x_shopify_topic} received for tenant {tenant_id}. Enqueueing processing.", 
            extra={"event_type": "shopify_webhook", "tenant_id": tenant_id}
        )
        from src.trueroas.workers.tasks import process_shopify_webhook_task
        process_shopify_webhook_task.delay(tenant_id, x_shopify_topic, payload)
        return {"status": "accepted", "topic": x_shopify_topic}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ignored", "topic": x_shopify_topic}
    )