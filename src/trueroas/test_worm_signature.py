#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

from src.trueroas.learning.worm_proof import PolicySigner
from typing import Dict, Any


def test_signature_canonicalization_idempotency() -> None:
    """
    WORM test: Generate same payload with different key orderings
    and verify signatures match (Canonicalization Test).
    """
    payload_a: Dict[str, Any] = {
        "break_even_roas": 3.3,
        "min_confidence_prob": 0.8,
        "tenant_id": "tenant_1",
    }

    payload_b: Dict[str, Any] = {
        "tenant_id": "tenant_1",
        "min_confidence_prob": 0.8,
        "break_even_roas": 3.3,
    }

    # Ensure inputs are actually different dict orders (though Python 3.7+ preserves order,
    # JSON serialization without sort_keys wouldn't)
    assert list(payload_a.keys()) != list(payload_b.keys())

    sig_a = PolicySigner.sign_policy(payload_a)
    sig_b = PolicySigner.sign_policy(payload_b)

    assert sig_a == sig_b
    assert len(sig_a) == 64  # Hex SHA256 length
