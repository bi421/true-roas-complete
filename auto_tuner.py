#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import logging
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any, Optional

import httpx
import jwt
from sqlalchemy.orm import Session

from src.trueroas.core.config import settings
from src.trueroas.core.database import SessionLocal
from .policy_store import PolicyStore
from .worm_proof import PolicySigner

logger = logging.getLogger("trueroas.learning.auto_tuner")


class AutoTuner:
    """
    Core algorithm for Bayesian threshold adjustment based on Brier Score.
    """

    @staticmethod
    def calculate_brier_score(predictions: List[Tuple[float, bool]]) -> float:
        """Brier = mean((confidence - outcome)^2)"""
        if not predictions:
            return 1.0

        total_sq_error = sum(
            (conf - float(outcome)) ** 2 for conf, outcome in predictions
        )
        return total_sq_error / len(predictions)

    @staticmethod
    def detect_systematic_bias(predictions: List[Tuple[float, bool]]) -> float:
        """bias = mean(predicted - actual)"""
        if not predictions:
            return 0.0

        total_bias = sum(conf - float(outcome) for conf, outcome in predictions)
        return total_bias / len(predictions)

    @staticmethod
    def compute_new_threshold(
        current: float, brier: float, bias: float, n: int
    ) -> float:
        """
        Deterministic threshold adjustment.
        Clamped to [0.4, 1.5] for stability.
        """
        new_threshold = current
        if brier > 0.25 and bias > 0.1:
            intensity = min(1.0, (bias - 0.1) / 0.4)
            adjustment = 0.05 + (0.10 * intensity)
            modifier = min(1.0, n / 50.0)
            new_threshold = current * (1.0 + (adjustment * modifier))

        return round(max(0.4, min(1.5, new_threshold)), 4)


def submit_learning_proof(tenant_id: str, payload: Dict[str, Any]) -> None:
    """Submits the auto-tuned policy update to the existing proof interface."""
    url = f"http://localhost:{settings.APP_PORT}/api/v1/proofs"

    # Generate internal JWT to satisfy API authentication
    token = jwt.encode(
        {
            "tenant_id": tenant_id,
            "role": "admin",
            "aud": "trueroas-api",
            "exp": int(datetime.now(timezone.utc).timestamp()) + 300,
        },
        settings.APP_SECRET_SALT,
        algorithm="HS256",
    )

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with httpx.Client() as client:
        try:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            logger.info(f"Successfully submitted POLICY_TUNE proof for {tenant_id}")
        except Exception as e:
            logger.error(f"Failed to submit learning proof for {tenant_id}: {e}")


def process_reconciled_batch(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Entry point for tuning logic processing a batch of reconciled decisions."""
    db: Session = SessionLocal()
    try:
        store = PolicyStore(db)
        if not store.is_enabled():
            return None

        audit_data = store.get_audit_trail_for_learning(tenant_id)
        if not audit_data:
            return None

        predictions = [
            (float(d["conf"]), bool(d["outcome"] in [1, True, "SUCCESS"]))
            for d in audit_data
        ]
        brier = AutoTuner.calculate_brier_score(predictions)
        bias = AutoTuner.detect_systematic_bias(predictions)

        latest_policy = store.get_latest_policy(tenant_id) or {"pause_threshold": 1.0}
        current_threshold = float(latest_policy.get("pause_threshold", 1.0))
        new_threshold = AutoTuner.compute_new_threshold(
            current_threshold, brier, bias, len(predictions)
        )

        if new_threshold == current_threshold:
            return {"status": "unchanged", "brier": round(brier, 4)}

        # Requirement C: Construct WORM-compliant payload
        proof_payload = {
            "true_roas": None,
            "meta_roas": None,
            "daily_spend": None,
            "waste_usd": None,
            "capital_health": "LEARNING_UPDATE",
            "action_required": "POLICY_TUNE",
            "cfo_brief": f"Auto-tuned threshold {current_threshold:.2f}→{new_threshold:.2f} (Brier {brier:.2f})",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        signature = PolicySigner.sign_policy(proof_payload)
        proof_payload["signature"] = signature

        submit_learning_proof(tenant_id, proof_payload)
        store.save_policy(tenant_id, {"pause_threshold": new_threshold}, signature)

        return {
            "status": "tuned",
            "new_threshold": new_threshold,
            "signature": signature,
        }
    finally:
        db.close()
