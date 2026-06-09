use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn update_threshold_from_brier(
    current_threshold: f64,
    brier_score: f64,
    bias: f64,
    sample_size: u32
) -> f64 {
    // Confidence modifier based on sample size to prevent over-fitting on small batches
    let modifier = if sample_size < 50 { 0.5 } else { 1.0 };
    
    let mut delta = 0.0;
    if brier_score > 0.25 {
        // Poor calibration: Increase threshold (tighten)
        delta = 0.05 * (1.0 + bias.abs());
    } else if brier_score < 0.10 {
        // High quality calibration: Lower threshold (more aggressive)
        delta = -0.02;
    }

    let result = current_threshold * (1.0 + (delta * modifier));
    (result * 100.0).round() / 100.0
}