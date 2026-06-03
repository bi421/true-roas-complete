import stripe
from fastapi import APIRouter, Depends, HTTPException
from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_session
from src.trueroas.core.subscriptions import SubscriptionService, SubscriptionTier

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])
stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/create-checkout-session")
async def create_checkout_session(plan_type: str, tenant_id: str, db: Session = Depends(get_db_session)):
    """
    Creates a Stripe Checkout session for Core ($79) or Accountability ($199).
    """
    price_id = settings.CORE_PLAN_PRICE_ID if plan_type == "core" else settings.ACCOUNTABILITY_PLAN_PRICE_ID
    
    try:
        # Ensure a tenant record exists for this prospect ID before creating checkout session
        # This allows linking the Stripe subscription back to a TrueROAS tenant
        SubscriptionService.create_subscription(
            db=db,
            tenant_id=tenant_id,
            plan_type=SubscriptionTier.CORE if plan_type == "core" else SubscriptionTier.ACCOUNTABILITY,
            stripe_customer_id=None # Will be updated by webhook
        )
        db.commit() # Commit the new tenant creation

        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f"{settings.TRUEROAS_API_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.TRUEROAS_API_URL}/cancel",
            client_reference_id=tenant_id,
            metadata={"tenant_id": tenant_id}
        )
        return {"url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))