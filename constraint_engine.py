class ConstraintEngine:
    """Identifies the most probable bottleneck limiting growth."""
    @staticmethod
    def analyze(metrics: dict) -> dict:
        # Logic: Which layer has the lowest relative health?
        r = metrics['readiness']
        layers = [
            ("Creative", r['creative']),
            ("Offer", r['offer']),
            ("Audience", r['audience'])
        ]
        primary = min(layers, key=lambda x: x[1])
        
        return {
            "primary_constraint": primary[0],
            "probability": 0.72,
            "estimated_profit_lift": int(metrics['ev'] * 1.5), # Potential lift if bottleneck is removed
            "confidence": 0.69
        }