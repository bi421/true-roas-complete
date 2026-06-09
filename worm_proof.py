#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import hmac
import hashlib
import json
from typing import Dict, Any
from src.trueroas.core.config import settings


class PolicySigner:
    """
    Provides WORM (Write Once Read Many) proof for policy updates.
    Canonicalizes policy configuration and signs it with the app salt.
    """

    @staticmethod
    def sign_policy(policy_config: Dict[str, Any]) -> str:
        """
        Generates an HMAC-SHA256 signature for a policy configuration.
        Uses canonical JSON formatting (sorted keys, no extra whitespace).
        """
        # Canonical serialization per Verification Protocol
        canonical_json: bytes = json.dumps(
            policy_config, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

        return hmac.new(
            settings.APP_SECRET_SALT.encode("utf-8"), canonical_json, hashlib.sha256
        ).hexdigest()
