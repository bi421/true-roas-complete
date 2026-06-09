#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text


class PolicyStore:
    """
    Handles read-only access to the decision audit trail for the self-learning system.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_audit_trail_for_learning(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Requirement B: Zero-Knowledge compliant read-only access to reconciled decisions.
        Queries predictions and outcomes from the last 14 days for policy auto-tuning.
        """
        query = text("""
            SELECT 
                expected_roas AS predicted_ev, 
                confidence_level AS predicted_confidence, 
                actual_outcome, 
                assumptions_json, 
                timestamp
            FROM decision_audit_trail
            WHERE tenant_id = :tid 
            AND reconciled_at > CURRENT_TIMESTAMP - INTERVAL '14 days'
        """)

        result = self.db.execute(query, {"tid": tenant_id}).fetchall()

        return [
            {
                "predicted_ev": row[0],
                "predicted_confidence": row[1],
                "actual_outcome": row[2],
                "assumptions_json": json.loads(row[3])
                if isinstance(row[3], str)
                else row[3],
                "timestamp": row[4],
            }
            for row in result
        ]
