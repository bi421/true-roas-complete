#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import base64
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any, Dict

import stripe
from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.trueroas.core.subscriptions import SubscriptionStatus
from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_session
from src.trueroas.core.subscriptions import (
    Tenant,
    SubscriptionService,
    SubscriptionTier,
    TenantStatus,
)
from src.trueroas.core.email_service import (
    send_payment_confirmation,
    send_payment_failure,
)

logger = logging.getLogger("trueroas.webhooks")
router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


def verify_shopify_signature(body: bytes, hmac_header: str) -> bool:
    """Verifies the HMAC signature provided by Shopify.

    Args:
        body (bytes): The raw request body.
        hmac_header (str): The 'X-Shopify-Hmac-Sha256' header value.

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    """
    Verifies the HMAC signature from Shopify to ensure request authenticity.
    """
    if not settings.SHOPIFY_API_SECRET:
        return False
    hash = hmac.new(settings.SHOPIFY_API_SECRET.encode(), body, hashlib.sha256).digest()
    expected_hmac = base64.b64encode(hash).decode()
    return hmac.compare_digest(expected_hmac, hmac_header)


async def verify_stripe_signature(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """Verifies the Stripe webhook signature and constructs the event object.

    Args:
        payload (bytes): The raw request payload.
        sig_header (str): The 'stripe-signature' header value.

    Returns:
        Dict[str, Any]: The verified Stripe event dictionary.
    """
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

    with get_db_session("default") as db:
        try:
            if event_type == "checkout.session.completed":
                await _handle_checkout_completed(db, event_data)
            elif event_type == "invoice.payment_succeeded":
                await _handle_payment_succeeded(db, event_data)
            elif event_type == "invoice.payment_failed":
                await _handle_payment_failed(db, event_data)
            elif event_type == "customer.subscription.deleted":
                await _handle_subscription_deleted(db, event_data)

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

    if not isinstance(tenant_id, str) or not tenant_id:
        logger.error("Missing client_reference_id in checkout session")
        raise ValueError("Missing tenant_id")
    if not isinstance(subscription_id, str) or not subscription_id:
        logger.error("Missing subscription in checkout session")
        raise ValueError("Missing subscription_id")

    stripe_sub = stripe.Subscription.retrieve(subscription_id, expand=["customer"])
    customer = stripe_sub.customer
    price_id = stripe_sub["items"]["data"][0]["price"]["id"]
    plan = (
        SubscriptionTier.STARTER
        if price_id == settings.CORE_PLAN_PRICE_ID
        else SubscriptionTier.PRO
    )

    SubscriptionService.activate_subscription(
        db=db,
        tenant_id=tenant_id,
        admin_email=customer.email,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        plan_type=plan,
        period_start=datetime.fromtimestamp(stripe_sub.current_period_start),
        period_end=datetime.fromtimestamp(stripe_sub.current_period_end),
    )
    await send_payment_confirmation(tenant_id, plan_type=plan.value)
    logger.info(f"Activated subscription for tenant {tenant_id}")


async def _handle_payment_succeeded(db: Session, invoice: Dict[str, Any]):
    """Renew subscription after successful payment."""
    subscription_id = invoice.get("subscription")
    sub = (
        db.query(Tenant)
        .filter(Tenant.stripe_subscription_id == subscription_id)
        .first()
    )
    if sub and isinstance(subscription_id, str):
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        sub.current_period_start = datetime.fromtimestamp(
            stripe_sub.current_period_start
        )
        sub.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        sub.status = TenantStatus.ACTIVE
        db.commit()
        logger.info(f"Renewed subscription for tenant {sub.slug}")


async def _handle_payment_failed(db: Session, invoice: Dict[str, Any]):
    """Mark subscription past due after failed payment."""
    subscription_id = invoice.get("subscription")
    sub = (
        db.query(Tenant)
        .filter(Tenant.stripe_subscription_id == subscription_id)
        .first()
    )
    if sub:
        SubscriptionService.mark_past_due(db, sub.slug)
        await send_payment_failure(
            sub.slug, retry_url=f"/billing/retry?tenant={sub.slug}"
        )
        logger.warning(f"Marked subscription past due for tenant {sub.slug}")


async def _handle_subscription_deleted(db: Session, subscription: Dict[str, Any]):
    """Cancel subscription when deleted in Stripe."""
    sub = (
        db.query(Tenant)
        .filter(Tenant.stripe_subscription_id == subscription["id"])
        .first()
    )
    if sub:
        SubscriptionService.cancel_subscription(db, sub.slug)
        logger.info(f"Canceled subscription for tenant {sub.slug}")


@router.post("/shopify")
async def shopify_webhook(
    request: Request,
    x_shopify_topic: str = Header(...),
    x_shopify_shop_domain: str = Header(...),
    x_shopify_hmac_sha256: str = Header(...),
):
    """FastAPI endpoint to handle Shopify webhook events.

    Args:
        request (Request): The incoming FastAPI request.
        x_shopify_topic (str): The webhook topic from headers.
        x_shopify_shop_domain (str): The shop domain from headers.
        x_shopify_hmac_sha256 (str): The HMAC signature from headers.

    Returns:
        dict: Information about the accepted or ignored webhook.
    """
    body = await request.body()
    if not verify_shopify_signature(body, x_shopify_hmac_sha256):
        logger.warning(
            f"Unauthorized Shopify Webhook attempt from {x_shopify_shop_domain}"
        )
        raise HTTPException(status_code=401, detail="Unauthorized")

    tenant_id = x_shopify_shop_domain.split(".")[0]
    payload = await request.json()

    if x_shopify_topic in ["orders/create", "orders/updated", "refunds/create"]:
        # Requirement: Observability matching SRE log patterns (grep "shopify_webhook")
        logger.info(
            f"Shopify webhook {x_shopify_topic} received for tenant {tenant_id}. Enqueueing processing.",
            extra={"event_type": "shopify_webhook", "tenant_id": tenant_id},
        )
        from src.trueroas.workers.tasks import process_shopify_webhook_task

        process_shopify_webhook_task.delay(tenant_id, x_shopify_topic, payload)
        return {"status": "accepted", "topic": x_shopify_topic}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ignored", "topic": x_shopify_topic},
    )
