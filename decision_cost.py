class DecisionCostEngine:
    """Estimates the financial cost of choosing the wrong action."""
    @staticmethod
    def calculate(proposed_increase: float, p_success: float, ev: float) -> dict:
        # If we scale but fail, we assume 80% of the incremental spend is lost capital.
        potential_loss = proposed_increase * 0.8
        # Risk-weighted cost of being wrong
        cost_of_error = potential_loss * (1 - p_success)
        
        return {
            "expected_gain": round(max(ev, 0), 2),
            "expected_loss": round(min(ev, 0), 2),
            "downside_risk": round(potential_loss, 2),
            "cost_of_error": round(cost_of_error, 2),
            "explanation": f"Choosing to scale carries a risk-weighted error cost of ${cost_of_error:,.2f} if the current variance persists."
        }