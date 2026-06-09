from typing import Any, Dict


class PolicyBootstrapper:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    @staticmethod
    def generate_initial_config(ratio: float) -> Dict[str, Any]:
        ratio = float(ratio)
        if ratio <= 0 or ratio >= 1:
            raise ValueError("Ratio must be in (0, 1)")
        return {
            "ratio": ratio,
            "threshold": ratio * 0.5,
            "learning_enabled": True,
            "min_samples": max(10, int(ratio * 100)),
            "break_even_roas": 4.0,
            "scale_threshold": 5.0,
            "pause_threshold": 3.6,
        }
