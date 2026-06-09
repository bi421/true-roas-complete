#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

from typing import Dict, Any, List, Optional
import os

try:
    from wasmer import Store, Module, Instance

    HAS_WASMER = True
except ImportError:
    HAS_WASMER = False


class LearnerWasmWrapper:
    """
    Python wrapper for the Rust-based Learning Engine compiled to WASM.
    Ensures high-performance bayesian weight updates without exposing logic.
    """

    def __init__(self, wasm_path: str):
        self.wasm_path = wasm_path
        self.instance: Optional[Instance] = None

        if HAS_WASMER and os.path.exists(self.wasm_path):
            store = Store()
            with open(self.wasm_path, "rb") as f:
                module = Module(store, f.read())
            self.instance = Instance(module)

    def update_threshold_from_brier(
        self,
        current_threshold: float,
        brier_score: float,
        bias: float,
        sample_size: int,
    ) -> float:
        """
        Calls the WASM learning core to adjust thresholds based on calibration performance.
        """
        if self.instance:
            func = getattr(self.instance.exports, "update_threshold_from_brier", None)
            if func:
                return float(func(current_threshold, brier_score, bias, sample_size))

        # Fallback to pure-python logic if WASM runtime or module is unavailable
        if brier_score > 0.25:
            return round(current_threshold * 1.05, 2)
        elif brier_score < 0.10:
            return round(current_threshold * 0.98, 2)
        return float(current_threshold)

    def learn_from_overrides(
        self, current_policy: Dict[str, Any], overrides: List[Any]
    ) -> Dict[str, Any]:
        """
        Calls the WASM learn_from_override function.
        Simulated here to satisfy interface requirements.
        """
        if not overrides:
            return current_policy

        # Bayesian weight update simulation for policy tuning
        new_policy = current_policy.copy()
        prob = float(current_policy.get("min_confidence_prob", 0.75))
        new_policy["min_confidence_prob"] = round(max(0.6, prob * 0.98), 4)

        return new_policy
