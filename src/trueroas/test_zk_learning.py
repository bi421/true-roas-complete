#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

from typing import Set
from trueroas.main import ZeroKnowledgeProofPayload


def test_zk_proof_payload_sanitization() -> None:
    """
    Zero-Knowledge test: Verify the ZeroKnowledgeProofPayload strictly
    excludes sensitive actual_outcome or PII fields as per architecture.
    """
    # Inspect Pydantic model fields
    model_fields = set(ZeroKnowledgeProofPayload.model_fields.keys())

    # 1. Assert no forbidden fields (Actual outcomes or PII)
    forbidden_keywords = {"actual", "outcome", "email", "pii", "user", "customer"}
    for field in model_fields:
        assert not any(kw in field.lower() for kw in forbidden_keywords), (
            f"Zero-Knowledge violation: field '{field}' contains sensitive metadata signature."
        )

    # 2. Assert strict adherence to allowed schema defined in Requirement 1
    ALLOWED_FIELDS: Set[str] = {
        "true_roas",
        "meta_roas",
        "waste_usd",
        "p10_roas",
        "timestamp",
        "signature",
    }
    assert model_fields.issubset(ALLOWED_FIELDS)
