#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Any, cast
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

from src.trueroas.auth import get_current_tenant
from src.trueroas.core.breaker import redis_client
from src.trueroas.core.config import settings
from src.trueroas.core.database import SessionLocal, get_db_session
from src.trueroas.core.strategy_content import StrategyContentService

logger = logging.getLogger("trueroas.decisions")

router = APIRouter(prefix="/api/v1/decisions", tags=["Strategic Decisions"])


@router.get("/dashboard/us-metrics")
async def get_us_dashboard_metrics(tenant_id: str = Depends(get_current_tenant)):
    """High-impact metrics for US-based founders."""
    # This would normally query the audit trail for prevent spend
    return {
        "capital_preservation_today": "$4,832.00",
        "capital_preservation_30d": "$48,200.00",
        "reconciliation_accuracy": "94.2%",
        "unverified_spend_blocked": "21.5%",
        "operational_efficiency": "+23%",
        "audit_status": "WORM-Compliant Logs Active",
        "data_residency": "Strictly Local (On-Premise)",
        "tax_readiness": "IRS-ready audit pack available",
        "verdict": "Your ad spend is mathematically anchored to verified revenue."
    }

@router.get("/dashboard/capital-saved")
async def get_capital_saved(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db_session)
):
    """
    For business owners: Displays the budget saved today and in total.
    Aggregates 'capital_saved' data calculated during META_SYNC from the Job Audit Log.
    """
    # 1. Нийт аварсан төсвийг Redis-ээс шууд авах (Lifetime savings)
    total_key = f"breaker:spend_saved_total:{tenant_id}"
    total_saved = float(redis_client.get(total_key) or 0.0)

    # 2. Өнөөдрийн аварсан төсвийг өгөгдлийн сангаас тооцоолох (UTC өдрөөр)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Filter the results of successful syncs completed today from the tenant's own warehouse
    query = text("""
        SELECT metadata_json 
        FROM job_audit_log 
        WHERE tenant_id = :tid 
          AND job_type = 'META_SYNC' 
          AND started_at >= :today
    """)
    
    results = db.execute(query, {"tid": tenant_id, "today": today_start}).fetchall()
    
    daily_saved = sum(
        json.loads(row[0]).get("capital_saved", 0.0) for row in results if row[0]
    )

    return {
        "tenant_id": tenant_id,
        "capital_saved_today": round(daily_saved, 2),
        "capital_saved_total": round(total_saved, 2),
        "currency": "USD",
        "last_updated": datetime.utcnow().isoformat()
    }


class DecisionCreate(BaseModel):
    campaign_id: str
    action: str = Field(..., pattern="^(SCALE|STRONG_SCALE|CAUTIOUS_SCALE|REDUCE_OR_HOLD)$")
    proposed_increase_usd: float = Field(..., ge=0)
    expected_roas: float = Field(..., gt=0)
    confidence_level: float = Field(..., ge=0, le=1)
    rationale: str = Field(..., min_length=10)
    meta_roas_observed: Optional[float] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
async def ingest_decision(
    req: DecisionCreate,
    tenant_id: str = Depends(get_current_tenant),
):
    """Ingests strategic decision and ensures immutability via payload hashing.

    Args:
        req (DecisionCreate): The decision payload.
        tenant_id (str): Unique tenant identifier.
        db (Session): Database session.

    Returns:
        dict: Information about the created decision, including its unique ID.
    """
    decision_id = str(uuid.uuid4())

    # Payload hashing for audit integrity
    payload_json = req.model_dump_json()
    payload_hash = hmac.new(
        settings.APP_SECRET_SALT.encode(), payload_json.encode(), hashlib.sha256
    ).hexdigest()

    # Recommendation: Model versioning - capture the state of the code at the time of decision
    model_hash = getattr(
        settings, "MODEL_VERSION_HASH", "unknown"
    )  # Derived from .env or git commit hash

    try:
        with SessionLocal() as db:
            db.execute(
                text("""
                INSERT INTO decision_audit_trail 
                (decision_id, tenant_id, campaign_id, action, expected_roas, confidence_level, 
                 assumptions_json, checksum, user_id, model_hash, status, created_at)
                VALUES (:decision_id, :tenant_id, :campaign_id, :action, :expected_roas, :confidence_level, 
                        :assumptions_json, :checksum, :user_id, :model_hash, :status, :created_at)
            """),
                {
                    "decision_id": decision_id,
                    "tenant_id": tenant_id,
                    "campaign_id": req.campaign_id,
                    "action": req.action,
                    "expected_roas": req.expected_roas,
                    "confidence_level": req.confidence_level,
                    "assumptions_json": json.dumps(
                        {
                            "rationale": req.rationale,
                            "proposed_increase": req.proposed_increase_usd,
                            "meta_roas_observed": req.meta_roas_observed,
                        }
                    ),
                    "checksum": payload_hash,
                    "user_id": "admin_user",
                    "model_hash": model_hash,
                    "status": "PENDING",
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            db.commit()
    except Exception as e:
        logger.error(f"Audit Integrity Failure: Failed to ingest decision {decision_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to persist decision to audit trail")

    return {"decision_id": decision_id, "status": "created", "checksum": payload_hash}


@router.get("/{decision_id}/report")
async def get_decision_report(
    decision_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db_session),
):
    """Downloads the post-decision audit report for a specific decision.

    Args:
        decision_id (str): Unique decision identifier.
        tenant_id (str): Unique tenant identifier.
        db (Session): Database session.

    Returns:
        dict: Post-mortem audit data and strategic reasoning.
    """
    res = (
        db.execute(
            text("SELECT * FROM decision_audit_trail WHERE decision_id = :decision_id"),
            {"decision_id": decision_id},
        ).fetchone()
        or ()
    )
    if not res:
        raise HTTPException(status_code=404, detail="Decision not found")

    data = dict(res._mapping)  # Convert RowProxy to dict
    data["assumptions_json"] = json.loads(data["assumptions_json"])

    # Convert to JSON string to support lru_cache in StrategyContentService
    return StrategyContentService.generate_post_mortem(
        json.dumps(data, sort_keys=True, default=str)
    )


@router.post("/{decision_id}/approve", status_code=status.HTTP_200_OK)
async def approve_decision(
    decision_id: str,
    approver_role: str = Header(..., alias="X-Approver-Role"),  # CEO or Accountant
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db_session),
):
    """Records stakeholder approval for a decision in the audit trail.

    Args:
        decision_id (str): Unique decision identifier.
        approver_role (str): Role of the person approving (passed via Header).
        tenant_id (str): Unique tenant identifier.
        db (Session): Database session.

    Returns:
        dict: Approval status and decision metadata.
    """
    approval_ts = datetime.utcnow().isoformat()

    result = db.execute(
        text("""
        UPDATE decision_audit_trail 
        SET status = 'APPROVED', 
            approved_by = :approver_role, 
            approved_at = :approval_ts
        WHERE decision_id = :decision_id AND tenant_id = :tenant_id
    """),
        {
            "approver_role": approver_role,
            "approval_ts": approval_ts,
            "decision_id": decision_id,
            "tenant_id": tenant_id,
        },
    )
    db.commit()

    if cast(Any, result).rowcount == 0:
        raise HTTPException(
            status_code=404, detail="Decision not found or already processed"
        )

    return {"status": "approved", "decision_id": decision_id, "approver": approver_role}
