import math


class EvidenceQualityEngine:
    """Justifies the confidence score by breaking down data integrity."""

    @staticmethod
    def score(match_rate: float, sample_size: int, volatility: float) -> dict:
        # Logarithmic scale for sample size: 100 orders is ~80 pts
        sample_quality = int(min(math.log10(max(sample_size, 1)) / 2.2, 1.0) * 100)

        # Penalty for high volatility (noise)
        volatility_penalty = int(min(volatility, 0.5) * -40)

        data_completeness = 95  # Placeholder for pixel vs server event parity

        # Weighted Average
        final_score = (
            (data_completeness * 0.3)
            + (match_rate * 100 * 0.3)
            + (sample_quality * 0.4)
            + volatility_penalty
        )

        return {
            "data_completeness": data_completeness,
            "match_rate": int(match_rate * 100),
            "sample_quality": sample_quality,
            "volatility_penalty": volatility_penalty,
            "evidence_quality": int(min(max(final_score, 0), 100)),
        }
