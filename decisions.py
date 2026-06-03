#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import uuid
import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.trueroas.core.database import get_db_session, get_db_path
from src.trueroas.auth import get_current_tenant
import duckdb

router = APIRouter(prefix="/api/v1/decisions", tags=["Strategic Decisions"])

class DecisionCreate(BaseModel):
    campaign_id: str
    action: str = Field(..., pattern="^(SCALE|PAUSE|OPTIMIZE)$")
    proposed_increase_usd: float = Field(..., ge=0)
    expected_roas: float = Field(..., gt=0)
    confidence_level: float = Field(..., ge=0, le=1)
    rationale: str = Field(..., min_length=10)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def ingest_decision(
    req: DecisionCreate,
    tenant_id: str = Depends(get_current_tenant)
):
    """Requirement 1: Ingest strategic decision and ensure immutability."""
    decision_id = str(uuid.uuid4())
    db_path = get_db_path(tenant_id)
    
    # Payload hashing for audit integrity
    payload_json = req.model_dump_json()
    payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

    with duckdb.connect(db_path) as con:
        con.execute("""
            INSERT INTO decision_audit_trail 
            (decision_id, tenant_id, campaign_id, action, expected_roas, confidence_level, 
             assumptions_json, checksum, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            decision_id, tenant_id, req.campaign_id, req.action, 
            req.expected_roas, req.confidence_level,
            json.dumps({"rationale": req.rationale, "proposed_increase": req.proposed_increase_usd}),
            payload_hash, "admin_user"
        ])

    return {"decision_id": decision_id, "status": "created", "checksum": payload_hash}