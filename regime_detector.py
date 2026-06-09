#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import statistics
from typing import List


class RegimeDetector:
    """Detects market volatility shifts for threshold relaxation."""

    @staticmethod
    def detect_cpm_regime(spend_history: List[float]) -> float:
        if len(spend_history) < 14:
            return 1.0

        avg_14d = statistics.mean(spend_history[-14:])
        avg_90d = statistics.mean(spend_history[-90:])

        if avg_90d > 0 and (avg_14d / avg_90d) > 1.5:
            return 1.2  # 20% relaxation multiplier
        return 1.0
