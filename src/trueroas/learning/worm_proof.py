import hmac
import hashlib
import json
from typing import Any
from src.trueroas.core.config import settings


class PolicySigner:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    @staticmethod
    def sign_policy(config: Any) -> str:
        """
        Generates an HMAC-SHA256 signature for a policy configuration.
        Uses canonical JSON formatting (sorted keys, no extra whitespace).
        """
        if isinstance(config, dict):
            canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
        else:
            canonical = str(config)

        return hmac.new(
            settings.APP_SECRET_SALT.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
