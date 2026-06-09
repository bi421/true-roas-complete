#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import json
from typing import Dict, Any, Optional, List, cast
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.trueroas.learning.config import learning_settings


class PolicyStore:
    """
    Handles PostgreSQL storage for strategic learning policies.
    Additive table 'learning_policies' stores deterministic threshold updates.
    """

    def __init__(self, db: Session):
        self.db = db

    def is_enabled(self) -> bool:
        """Checks the LEARNING_ENABLED feature flag from environment."""
        return learning_settings.learning_enabled

    def save_policy(
        self, tenant_id: str, config: Dict[str, Any], signature: str
    ) -> None:
        """
        Persists a new policy configuration and its WORM signature to PostgreSQL.
        """
        if not self.is_enabled():
            return

        query = text("""
            INSERT INTO learning_policies (tenant_id, config_json, signature, created_at)
            VALUES (:tenant_id, :config_json, :signature, CURRENT_TIMESTAMP)
        """)
        if self.db:
            self.db.execute(
                query,
                {
                    "tenant_id": tenant_id,
                    "config_json": json.dumps(config, sort_keys=True),
                    "signature": signature,
                },
            )
            # Remove explicit commit here to allow the caller
            # (process_reconciled_batch) to manage the transaction lifecycle.
            # self.db.commit()
            pass

    def get_latest_policy(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent policy for a specific tenant from PostgreSQL."""
        if not self.db:
            return None

        query = text("""
            SELECT config_json FROM learning_policies 
            WHERE tenant_id = :tenant_id 
            ORDER BY id DESC LIMIT 1
        """)
        result = self.db.execute(query, {"tenant_id": tenant_id}).fetchone()
        if result:
            # Explicit cast to Dict[str, Any] ensures type safety for the caller (AutoTuner)
            return cast(Dict[str, Any], json.loads(str(result[0])))
        return None

    def get_audit_trail_for_learning(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Read-only access to decision_audit_trail for Bayesian input."""
        if not self.db:
            return []

        # Handle both PostgreSQL and SQLite interval syntax for cross-env stability
        dialect = self.db.get_bind().dialect.name

        if dialect == "sqlite":
            sql = (
                "SELECT expected_roas, confidence_level, actual_roas_7d FROM decision_audit_trail "
                "WHERE tenant_id = :tenant_id AND reconciled_7d_at > date('now', '-14 days') "
                "AND actual_roas_7d IS NOT NULL"
            )
        else:
            sql = (
                "SELECT expected_roas, confidence_level, actual_roas_7d FROM decision_audit_trail "
                "WHERE tenant_id = :tenant_id AND reconciled_7d_at > CURRENT_TIMESTAMP - INTERVAL '14 days' "
                "AND actual_roas_7d IS NOT NULL"
            )

        query = text(sql)
        rows = self.db.execute(query, {"tenant_id": tenant_id}).fetchall()
        return [{"ev": row[0], "conf": row[1], "outcome": row[2]} for row in rows]
