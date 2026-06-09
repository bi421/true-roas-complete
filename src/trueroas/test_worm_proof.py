#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

from trueroas.learning.worm_proof import PolicySigner


def test_policy_signing_idempotency() -> None:
    config = {"threshold": 2.5, "tenant": "test"}
    sig1 = PolicySigner.sign_policy(config)
    sig2 = PolicySigner.sign_policy(config)
    assert sig1 == sig2

    config_changed = {"threshold": 2.6, "tenant": "test"}
    sig3 = PolicySigner.sign_policy(config_changed)
    assert sig1 != sig3
