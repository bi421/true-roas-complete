#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import redis
import time
import json
import logging
from datetime import datetime
from src.trueroas.core.config import settings
from src.trueroas.core.database import get_db_path
from prometheus_client import Counter
import duckdb

logger = logging.getLogger("trueroas.breaker")
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

CIRCUIT_BREAKER_TRIGGERS = Counter(
    "circuit_breaker_triggers_total", "Total circuit breaker trigger events", ["tenant_id", "campaign_id", "severity"]
)

class AdSpendBreaker:
    """
    Production-grade circuit breaker for ad spend protection.
    Monitors variance windows in Redis and triggers automated actions.
    """

    @staticmethod
    def record_variance(tenant_id: str, campaign_id: str, meta_roas: float, true_roas: float):
        """Records a real-time variance observation into Redis buckets."""
        if meta_roas <= 0: return
        
        variance = abs(meta_roas - true_roas) / meta_roas
        now = int(time.time())
        key = f"breaker:variance:{tenant_id}:{campaign_id}"
        
        try:
            # Store (timestamp, variance) in sorted set
            redis_client.zadd(key, {f"{now}:{variance}": now})
            
            # TTL set to max window + buffer (2 hours)
            redis_client.expire(key, 7200)
            # Clean old buckets
            redis_client.zremrangebyscore(key, 0, now - 7200)
        except redis.exceptions.RedisError as e:
            logger.error(f"Circuit breaker failed to record to Redis: {e}. Falling back to local logging.")
            # Requirement 2.d: Persist to local SQLite fallback on failure/eviction
            AdSpendBreaker.log_decision(tenant_id, campaign_id, "CB_RECORD_FALLBACK", f"Redis offline. Local variance: {variance:.2%}")

    @staticmethod
    def evaluate(tenant_id: str, campaign_id: str) -> dict:
        """Evaluates SOFT and HARD thresholds over sliding windows."""
        now = int(time.time())

        # Requirement 10: Check for active manual override
        override_key = f"breaker:override:{tenant_id}:{campaign_id}"
        if redis_client.get(override_key):
            return {
                "status": "OVERRIDE_ACTIVE",
                "hard_avg": 0.0,
                "soft_avg": 0.0,
                "timestamp": now
            }

        key = f"breaker:variance:{tenant_id}:{campaign_id}"
        
        def get_avg_variance(minutes: int) -> float:
            data = redis_client.zrangebyscore(key, now - (minutes * 60), now)
            if not data: return 0.0
            variances = [float(item.split(":")[1]) for item in data]
            return sum(variances) / len(variances)

        hard_avg = get_avg_variance(settings.CB_HARD_WINDOW_MINS)
        soft_avg = get_avg_variance(settings.CB_SOFT_WINDOW_MINS)

        status = "HEALTHY"
        if hard_avg > settings.CB_HARD_VARIANCE_THRESHOLD:
            status = "HARD_BREAKER"
            CIRCUIT_BREAKER_TRIGGERS.labels(tenant_id=tenant_id, campaign_id=campaign_id, severity="HARD").inc()
        elif soft_avg > settings.CB_SOFT_VARIANCE_THRESHOLD:
            status = "SOFT_BREAKER"
            CIRCUIT_BREAKER_TRIGGERS.labels(tenant_id=tenant_id, campaign_id=campaign_id, severity="SOFT").inc()

        return {
            "status": status,
            "hard_avg": round(hard_avg, 3),
            "soft_avg": round(soft_avg, 3),
            "timestamp": now
        }

    @staticmethod
    def log_decision(tenant_id: str, campaign_id: str, action: str, details: str):
        """Persists the circuit breaker action to the decision audit trail."""
        db_path = get_db_path(tenant_id)
        import uuid
        decision_id = f"auto_{uuid.uuid4().hex[:8]}"
        
        with duckdb.connect(db_path) as con:
            con.execute("""
                INSERT INTO decision_audit_trail 
                (decision_id, tenant_id, campaign_id, action, expected_roas, confidence_level, assumptions_json, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [decision_id, tenant_id, campaign_id, action, 0.0, 1.0, 
                  json.dumps({"trigger": "circuit_breaker", "details": details}), "SYSTEM_AUTO"])

    @staticmethod
    def reset(tenant_id: str, campaign_id: str):
        """Clears the variance history for a campaign."""
        key = f"breaker:variance:{tenant_id}:{campaign_id}"
        redis_client.delete(key)
        logger.info(f"Circuit breaker manually reset for {tenant_id}:{campaign_id}")

    @staticmethod
    def set_override(tenant_id: str, campaign_id: str, duration_mins: int):
        """Sets a temporary override key in Redis with the specified duration."""
        key = f"breaker:override:{tenant_id}:{campaign_id}"
        redis_client.set(key, "1", ex=duration_mins * 60)
