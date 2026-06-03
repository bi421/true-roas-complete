import logging
from fastapi import APIRouter, Request, Header, status
from src.trueroas.workers.tasks import sync_meta_data

logger = logging.getLogger("trueroas.webhooks")
router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

@router.post("/shopify")
async def shopify_webhook(
    request: Request, 
    x_shopify_topic: str = Header(...),
    x_shopify_shop_domain: str = Header(...)
):
    """
    Real-time Shopify webhook handler.
    Triggers incremental reconciliation when orders or refunds are created.
    """
    # tenant_id is derived from shop domain in a real SaaS environment
    tenant_id = x_shopify_shop_domain.split('.')[0]
    
    if x_shopify_topic in ["orders/create", "orders/updated", "refunds/create"]:
        logger.info(f"Webhook {x_shopify_topic} received for {tenant_id}. Triggering sync.")
        # Trigger immediate background sync for current data
        sync_meta_data.delay(tenant_id)
        return {"status": "accepted", "topic": x_shopify_topic}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ignored", "topic": x_shopify_topic}
    )