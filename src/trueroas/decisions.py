#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, Any, Dict

import anyio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
import duckdb
from trueroas.auth import get_current_tenant, get_auth_context
from trueroas.core.database import get_db_session, get_db_path
from trueroas.core.strategy_content import StrategyContentService

router = APIRouter(tags=["Strategic Decisions"])


class DecisionCreate(BaseModel):
    campaign_id: str
    action: str = Field(..., pattern="^(SCALE|PAUSE|OPTIMIZE)$")
    proposed_increase_usd: float = Field(..., ge=0)
    expected_roas: float = Field(..., gt=0)
    confidence_level: float = Field(..., ge=0, le=1)
    rationale: str = Field(..., min_length=10)
    meta_roas_observed: Optional[float] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
async def ingest_decision(
    req: DecisionCreate,
    auth_payload: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Requirement 1: Ingest strategic decision and ensure immutability."""
    tenant_id = auth_payload["tenant_id"]
    user_id = auth_payload.get("sub", "unknown_user")
    decision_id = str(uuid.uuid4())

    # Payload hashing for audit integrity
    payload_json = req.model_dump_json()
    payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

    def _persist() -> None:
        db_path = get_db_path(tenant_id)
        with duckdb.connect(db_path) as con:
            con.execute(
                """
            INSERT INTO decision_audit_trail 
            (decision_id, tenant_id, campaign_id, action, expected_roas, confidence_level, 
             assumptions_json, checksum, user_id, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', CURRENT_TIMESTAMP)
        """,
                [
                    decision_id,
                    tenant_id,
                    req.campaign_id,
                    req.action,
                    req.expected_roas,
                    req.confidence_level,
                    json.dumps(
                        {
                            "rationale": req.rationale,
                            "proposed_increase": req.proposed_increase_usd,
                            "meta_roas_observed": req.meta_roas_observed,
                        }
                    ),
                    payload_hash,
                    user_id,
                ],
            )

    await anyio.to_thread.run_sync(_persist)

    return {"decision_id": decision_id, "status": "created", "checksum": payload_hash}


@router.get("/{decision_id}/report")
async def get_decision_report(
    decision_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Download the post-decision audit report."""
    res = (
        db.execute(
            text(
                "SELECT * FROM decision_audit_trail WHERE decision_id = :decision_id AND tenant_id = :tenant_id"
            ),
            {"decision_id": decision_id, "tenant_id": tenant_id},
        ).fetchone()
        or ()
    )
    if not res:
        raise HTTPException(status_code=404, detail="Decision not found")

    data = dict(res._mapping)
    data["assumptions_json"] = json.loads(data["assumptions_json"])

    # Convert to JSON string with sorted keys to support lru_cache in StrategyContentService
    result = StrategyContentService.generate_post_mortem(
        json.dumps(data, sort_keys=True, default=str)
    )
    return dict(result) if result else {}


@router.post("/{decision_id}/approve", status_code=status.HTTP_200_OK)
async def approve_decision(
    decision_id: str,
    auth_payload: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    tenant_id = auth_payload["tenant_id"]
    approver_role = auth_payload.get("role", "viewer")
    approval_ts = datetime.utcnow().isoformat()
    db.execute(
        text("""
        UPDATE decision_audit_trail 
        SET status = 'APPROVED', approved_by = :approver_role, approved_at = :approval_ts
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
    return {"status": "approved", "decision_id": decision_id}
