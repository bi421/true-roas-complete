class WhatMustBeTrueEngine:
    """Generates the conditions required for a strategy to succeed."""

    @staticmethod
    def generate(action: str, ctr: float, cr: float, match_rate: float) -> list:
        if "HOLD" in action or "REDUCE" in action:
            return [
                "Attribution variance must be investigated",
                "Match Rate must exceed 85% for better reconciliation",
            ]

        # Scaling conditions
        return [
            f"CTR > {round(ctr * 0.95, 3)}% (Creative floor)",
            f"Conversion Rate > {round(cr * 0.9, 3)}% (Offer stability)",
            "Audience Saturation < 70% (Frequency ceiling)",
            f"Match Rate > {max(int(match_rate * 100), 80)}% (Data integrity)",
        ]
