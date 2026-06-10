use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn generate_proof(meta_spend: f64, shopify_rev: f64) -> f64 {
    if meta_spend == 0.0 { return 0.0; }
    shopify_rev / meta_spend
}

#[wasm_bindgen]
pub fn version() -> String {
    "TrueROAS v0.1".into()
}