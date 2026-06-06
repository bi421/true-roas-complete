# Bot Traffic and Fraud Defense Module
from typing import Any, Dict

from .market_config import Settings


class BotDefenseEngine:
    """Analyzes click and conversion behavior to identify traffic quality risks."""

    @staticmethod
    def perform_security_audit(
        ctr: float, cvr: float, frequency: float
    ) -> Dict[str, Any]:
        risk_score = 0.0
        warnings = []

        # Monitor for malicious bot clicks (High CTR, Low CVR)
        if ctr > Settings.bot_ctr_threshold:
            risk_score += 0.5
            warnings.append(f"Abnormally high CTR: {ctr:.1%}")

        if ctr > 0.06 and cvr < 0.003:
            risk_score += 0.3
            warnings.append("Typical bot profile: High clicks with no conversion")

        # Monitor for suspected click-farming (Extremely high CVR)
        if cvr > Settings.fraud_cvr_alert_line:
            risk_score += 0.6
            warnings.append(
                f"Suspected manual fraud: CVR {cvr:.1%} exceeds natural levels"
            )

        # Frequency check
        if frequency > Settings.benchmark_frequency:
            risk_score += 0.2
            warnings.append("Audience over-saturation, traffic value decaying")

        risk_level = "Safe"
        if risk_score >= 0.8:
            risk_level = "Critical"
        elif risk_score >= 0.4:
            risk_level = "Medium"

        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "warning_items": warnings,
            "data_reliability": round(1.0 - min(risk_score, 0.9), 2),
        }

    @staticmethod
    def adjust_roi(original_roi: float, risk_score: float) -> float:
        """Applies penalties to ROI based on risk levels."""
        if risk_score >= 0.8:
            return original_roi * 0.4  # Critical risk: massive ROI reduction
        if risk_score >= 0.4:
            return original_roi * Settings.defense_deduction_factor
        return original_roi
