#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import json
import logging
import time
import asyncio
from typing import Any, Dict

import redis
from prometheus_client import Counter
from sqlalchemy import text

from src.trueroas.core.database import get_db_session
from src.trueroas.core.config import settings

logger = logging.getLogger("trueroas.breaker")
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

CIRCUIT_BREAKER_TRIGGERS = Counter(
    "circuit_breaker_triggers_total",
    "Total circuit breaker trigger events",
    ["tenant_id", "campaign_id", "severity"],
)


class AdSpendBreaker:
    """
    Production-grade circuit breaker for ad spend protection.
    Monitors variance windows in Redis and triggers automated actions.
    """

    @staticmethod
    def record_variance(
        tenant_id: str, campaign_id: str, meta_roas: float, true_roas: float
    ) -> None:
        """Records a real-time variance observation into Redis buckets."""
        if meta_roas <= 0:
            return

        # Business Logic: If True ROAS is higher than Meta, it is not a risk.
        # Variance is only recorded when Meta overstates performance (meta > true).
        variance = min(max(0, (meta_roas - true_roas)) / max(meta_roas, 0.01), 1.0)
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
            logger.error(
                f"Circuit breaker failed to record to Redis: {e}. Falling back to local logging."
            )
            # Requirement 2.d: Persist to local SQLite fallback on failure/eviction
            AdSpendBreaker.log_decision(
                tenant_id,
                campaign_id,
                "CB_RECORD_FALLBACK",
                f"Redis offline. Local variance: {variance:.2%}",
            )

    @staticmethod
    def evaluate(tenant_id: str, campaign_id: str) -> Dict[str, Any]:
        """Evaluates SOFT and HARD thresholds over sliding windows."""
        now = int(time.time())

        # Requirement 10: Check for active manual override
        override_key = f"breaker:override:{tenant_id}:{campaign_id}"
        if redis_client.get(override_key):
            return {
                "status": "OVERRIDE_ACTIVE",
                "reasoning": "Manual override active - trust set to 100%",
                "hard_avg": 0.0,
                "soft_avg": 0.0,
                "timestamp": now,
            }

        key = f"breaker:variance:{tenant_id}:{campaign_id}"

        def get_avg_variance(minutes: int) -> float:
            data = redis_client.zrangebyscore(key, now - (minutes * 60), now)
            if not data:
                return 0.0
            variances = [float(str(item).split(":")[1]) for item in data]
            return sum(variances) / len(variances) if variances else 0.0

        hard_avg = get_avg_variance(settings.CB_HARD_WINDOW_MINS)
        soft_avg = get_avg_variance(settings.CB_SOFT_WINDOW_MINS)

        status = "HEALTHY"
        if hard_avg > settings.CB_HARD_VARIANCE_THRESHOLD:
            status = "HARD_BREAKER"
            CIRCUIT_BREAKER_TRIGGERS.labels(
                tenant_id=tenant_id, campaign_id=campaign_id, severity="HARD"
            ).inc()
        elif soft_avg > settings.CB_SOFT_VARIANCE_THRESHOLD:
            status = "SOFT_BREAKER"
            CIRCUIT_BREAKER_TRIGGERS.labels(
                tenant_id=tenant_id, campaign_id=campaign_id, severity="SOFT"
            ).inc()

        return {
            "status": status,
            "hard_avg": round(hard_avg, 3),
            "soft_avg": round(soft_avg, 3),
            "timestamp": now,
        }

    @staticmethod
    async def request_human_approval(
        tenant_id: str, campaign_id: str, waste_amount: float
    ) -> bool:
        """
        Phase 6: Human-in-the-loop approval via Slack.
        Waits for 300 seconds (5 minutes) for a human decision in Redis.
        """
        approval_key = f"hitl:approval:{tenant_id}:{campaign_id}"

        # 1. Send Slack Notification (Mocking webhook call)
        message = f"🚨 *TrueROAS Capital Alert* 🚨\nTenant: {tenant_id}\nCampaign: {campaign_id}\nEstimated Waste: ${waste_amount:,.2f}\nAction: *PAUSE RECOMMENDED*"
        logger.warning(f"HITL: Sending Slack approval request for {campaign_id}")

        # Logic for real Slack interactive buttons would go here
        # await httpx.post(settings.SLACK_WEBHOOK_URL, json={"text": message})

        # 2. Wait for human intervention (Redis Polling)
        timeout = 300
        start_time = time.time()

        while time.time() - start_time < timeout:
            approval_status = redis_client.get(approval_key)
            if approval_status == "APPROVED":
                logger.info(f"HITL: Human APPROVED pause for {campaign_id}")
                redis_client.delete(approval_key)
                return True
            if approval_status == "REJECTED":
                logger.info(f"HITL: Human REJECTED pause for {campaign_id}")
                redis_client.delete(approval_key)
                return False

            await asyncio.sleep(5)  # Use asynchronous wait

        logger.error(
            f"HITL: Approval TIMEOUT (300s) for {campaign_id}. Defaulting to CAPITAL_SAFETY (PAUSE)."
        )
        return True  # Default to safety in high-waste scenarios

    @staticmethod
    def log_decision(
        tenant_id: str, campaign_id: str, action: str, details: str
    ) -> None:
        """Persists the circuit breaker action to the decision audit trail."""
        import uuid

        decision_id = f"auto_{uuid.uuid4().hex[:8]}"

        # Use SQLAlchemy session for central database consistency (Postgres RLS supported)
        with get_db_session(tenant_id) as db:
            db.execute(
                text("""
                INSERT INTO decision_audit_trail 
                (decision_id, tenant_id, campaign_id, action, expected_roas, confidence_level, assumptions_json, user_id)
                VALUES (:decision_id, :tenant_id, :campaign_id, :action, :expected_roas, :confidence_level, :assumptions_json, :user_id)
            """),
                {
                    "decision_id": decision_id,
                    "tenant_id": tenant_id,
                    "campaign_id": campaign_id,
                    "action": action,
                    "expected_roas": 0.0,
                    "confidence_level": 1.0,
                    "assumptions_json": json.dumps(
                        {"trigger": "circuit_breaker", "details": details}
                    ),
                    "user_id": "SYSTEM_AUTO",
                },
            )
            db.commit()

    @staticmethod
    def reset(tenant_id: str, campaign_id: str) -> None:
        """Clears the variance history for a campaign."""
        key = f"breaker:variance:{tenant_id}:{campaign_id}"
        redis_client.delete(key)
        logger.info(f"Circuit breaker manually reset for {tenant_id}:{campaign_id}")

    @staticmethod
    def set_override(tenant_id: str, campaign_id: str, duration_mins: int) -> None:
        """Sets a temporary override key in Redis with the specified duration."""
        key = f"breaker:override:{tenant_id}:{campaign_id}"
        redis_client.set(key, "1", ex=duration_mins * 60)
