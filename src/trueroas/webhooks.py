import logging
from fastapi import APIRouter, Request, Header, status
from fastapi.responses import JSONResponse
from typing import Dict, Union

logger = logging.getLogger("trueroas.webhooks")
router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


@router.post("/shopify", response_model=None)
async def shopify_webhook(
    request: Request,
    x_shopify_topic: str = Header(...),
    x_shopify_shop_domain: str = Header(...),
) -> Union[Dict[str, str], JSONResponse]:
    """
    Real-time Shopify webhook handler.
    Triggers incremental reconciliation when orders or refunds are created.
    """
    # tenant_id is derived from shop domain in a real SaaS environment
    tenant_id = x_shopify_shop_domain.split(".")[0]

    if x_shopify_topic in ["orders/create", "orders/updated", "refunds/create"]:
        logger.info(
            f"Webhook {x_shopify_topic} received for {tenant_id}. Triggering sync."
        )
        # Inbound data sync deprecated in Zero-Knowledge mode.
        return {"status": "ignored", "message": "Inbound data sync deprecated."}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ignored", "topic": x_shopify_topic},
    )
