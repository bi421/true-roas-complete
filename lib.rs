use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn tune_threshold(current: f64, brier: f64, bias: f64) -> f64 {
    let mut new_threshold = current;

    // Calibration check logic for Bayesian threshold adjustment.
    // Derived from the Zero-Touch Self-Learning System's AutoTuner logic.
    // If calibration is poor (brier > 0.25) and system is over-optimistic (bias > 0.1),
    // we increase the threshold to tighten decision criteria.
    if brier > 0.25 && bias > 0.1 {
        // Intensity scales linearly with bias magnitude (capped at 0.5)
        let intensity = ((bias - 0.1) / 0.4).min(1.0).max(0.0);
        
        // Apply a deterministic adjustment between 5% and 15%
        let adjustment = 0.05 + (0.10 * intensity);
        
        // Note: Sample size dampening is typically handled at the orchestration layer 
        // before calling the WASM core for the final adjustment.
        new_threshold = current * (1.0 + adjustment);
    }

    // Clamp to [0.4, 1.5] range to prevent extreme drift and ensure stability.
    let clamped = new_threshold.clamp(0.4, 1.5);
    (clamped * 10000.0).round() / 10000.0
}