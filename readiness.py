class DecisionReadinessEngine:
    """Evaluates business capacity to absorb scale."""
    @staticmethod
    def evaluate(ctr: float, cr: float, freq: float, b_ctr: float, b_cr: float) -> dict:
        # Scores relative to benchmarks
        creative_score = int(min(ctr / max(b_ctr, 0.001), 1.2) * 83)
        offer_score = int(min(cr / max(b_cr, 0.001), 1.2) * 83)
        audience_score = int(max(0, 1.0 - (freq / 4.0)) * 100)
        tracking_score = 91 # Placeholder for CAPI health
        
        # Weighted readiness
        readiness = (creative_score * 0.3) + (offer_score * 0.3) + (audience_score * 0.2) + (tracking_score * 0.2)
        
        return {
            "readiness_score": int(readiness),
            "audience": audience_score,
            "creative": creative_score,
            "offer": offer_score,
            "tracking": tracking_score
        }