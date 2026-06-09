#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

httpx: Any = None
try:
    import httpx as _httpx

    httpx = _httpx
except ImportError:
    httpx = None

logger = logging.getLogger("trueroas.learning.auto_tuner")


class AutoTuner:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    @staticmethod
    def calculate_brier_score(predictions: List[Tuple[float, bool]]) -> float:
        if not predictions:
            return 0.25  # Neutral Brier score (max uncertainty)
        total = 0.0
        for prob, outcome in predictions:
            actual = 1.0 if outcome else 0.0
            total += (float(prob) - actual) ** 2
        return total / len(predictions)

    @staticmethod
    def compute_new_threshold(
        current: float, brier: float, bias: float, n: int
    ) -> float:
        current = float(current)
        brier = float(brier)
        bias = float(bias)
        n = int(n) if n else 1
        # Weigh the adjustment by sample size to avoid over-reacting to small noise
        confidence_weight = min(1.0, n / 100.0)
        adjustment = ((0.5 - brier) * 0.1 + bias * 0.05) * confidence_weight
        # Clamping logic: ensure results stay within [0.4, 1.5] and round for stability
        return round(max(0.4, min(1.5, current + adjustment)), 4)

    @staticmethod
    def detect_systematic_bias(predictions: List[Tuple[float, bool]]) -> float:
        if not predictions:
            return 0.0
        total = 0.0
        for prob, outcome in predictions:
            actual = 1.0 if outcome else 0.0
            total += float(prob) - actual
        return total / len(predictions)


def submit_learning_proof(tenant_id: str, payload: Dict[str, Any]) -> None:
    """Submits the auto-tuned policy update to the internal API."""
    from trueroas.core.config import settings
    import jwt

    # Use internal service name or setting for consistency in Docker/K8s
    api_host = getattr(
        settings, "INTERNAL_API_URL", f"http://localhost:{settings.APP_PORT}"
    )
    url = f"{api_host}/api/v1/proofs"

    if httpx is None:
        logger.error("httpx is not installed. Learning proof submission skipped.")
        return

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
            client.post(url, json=payload, headers=headers)
        except Exception as e:
            logger.error(f"Failed to submit learning proof: {e}")


def process_reconciled_batch(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Logic entry point for tuning logic processing a batch of reconciled decisions."""
    from .policy_store import PolicyStore
    from .config import learning_settings
    from .worm_proof import PolicySigner
    from ..core.database import SessionLocal
    from sqlalchemy.orm import Session

    db: Session = SessionLocal()
    try:
        store = PolicyStore(db)
        if not learning_settings.learning_enabled:
            return None

        audit_data = store.get_audit_trail_for_learning(tenant_id)
        # Threshold for minimum samples to prevent noise-based tuning
        if not audit_data or len(audit_data) < 5:
            return None

        def _safe_float(val: Any) -> float:
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # Logic: Check if actual ROAS met the expected target (EV)
        # Added safety check for 'ev' and 'outcome' being numeric or categorical (SUCCESS/FAILURE)
        predictions: List[Tuple[float, bool]] = []
        for d in audit_data:
            conf = _safe_float(d.get("conf", 0))
            ev = _safe_float(d.get("ev", 1.0))
            outcome_val = d.get("outcome", 0)

            # Handle categorical outcomes often found in tests or legacy logs
            if (
                isinstance(outcome_val, str)
                and not outcome_val.replace(".", "", 1).isdigit()
            ):
                success = outcome_val.upper() in ("SUCCESS", "OK", "TRUE")
            else:
                success = _safe_float(outcome_val) >= ev

            predictions.append((conf, success))

        brier = AutoTuner.calculate_brier_score(predictions)
        bias = AutoTuner.detect_systematic_bias(predictions)

        latest_policy = store.get_latest_policy(tenant_id)
        if not latest_policy:
            latest_policy = {"pause_threshold": 1.0}

        current_threshold = float(latest_policy.get("pause_threshold", 1.0))
        new_threshold = AutoTuner.compute_new_threshold(
            current_threshold, brier, bias, len(predictions)
        )

        if abs(new_threshold - current_threshold) < 0.0001:
            return {"status": "unchanged", "brier": round(brier, 4)}

        proof_payload = {
            "true_roas": None,
            "meta_roas": None,
            "waste_usd": None,
            "p10_roas": None,
            "capital_health": "LEARNING_UPDATE",
            "action_required": "POLICY_TUNE",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        signature = PolicySigner.sign_policy(proof_payload)
        proof_payload["signature"] = signature

        try:
            # Submit proof before saving to ensure consistency
            submit_learning_proof(tenant_id, proof_payload)
            store.save_policy(tenant_id, {"pause_threshold": new_threshold}, signature)
            db.commit()  # Finalize the transaction to persist the new policy
            return {"status": "tuned", "new_threshold": new_threshold}
        except Exception as e:
            logger.error(f"Failed to commit tuned policy for {tenant_id}: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}
    finally:
        db.close()
