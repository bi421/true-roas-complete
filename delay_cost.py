class DecisionDelayEngine:
    """Estimates the profit lost by waiting too long to act."""
    @staticmethod
    def calculate(ev: float) -> dict:
        # EV represents the total value of the move. 
        # We assume a standard 7-day implementation cycle for the daily rate.
        daily_opportunity = max(ev / 7.0, 0)
        
        # Delay impact is usually non-linear due to compounding/market shifts, 
        # but we start with a linear opportunity cost.
        return {
            "delay_7_days": round(daily_opportunity * 7, 2),
            "delay_14_days": round(daily_opportunity * 14, 2),
            "delay_30_days": round(daily_opportunity * 30, 2),
            "urgency_score": int(min(daily_opportunity / 100, 1.0) * 100)
        }