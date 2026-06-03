import hmac
import hashlib
import base64
import pytest
from src.trueroas.workers.webhooks import verify_shopify_signature
from src.trueroas.core.config import settings

def test_shopify_signature_verification():
    """Verifies HMAC calculation for Shopify webhooks."""
    settings.SHOPIFY_API_SECRET = "test_secret"
    body = b'{"id": 123}'
    
    # Calculate expected HMAC
    hash = hmac.new(b"test_secret", body, hashlib.sha256).digest()
    valid_hmac = base64.b64encode(hash).decode()
    
    assert verify_shopify_signature(body, valid_hmac) is True
    assert verify_shopify_signature(body, "wrong_hmac") is False

def test_subscription_db_initialization():
    """Ensures central DB models are correctly mapped."""
    from src.trueroas.core.database import SessionLocal
    from src.trueroas.core.subscriptions import Subscription
    
    db = SessionLocal()
    try:
        # Test query to ensure table exists
        count = db.query(Subscription).count()
        assert isinstance(count, int)
    finally:
        db.close()