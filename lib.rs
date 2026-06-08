//  Copyright (c) 2024-2026 TrueROAS Team.
//  Zero-Knowledge Client-Side Compute Engine (WASM)

use wasm_bindgen::prelude::*;
use statrs::distribution::{Continuous, ContinuousCDF, Normal};
use serde::{Serialize, Deserialize};

#[wasm_bindgen]
#[derive(Serialize, Deserialize)]
pub struct BayesianResult {
    pub true_roas: f64,
    pub meta_roas: f64,
    pub waste_usd: f64,
    pub p10_roas: f64,
}

#[wasm_bindgen]
pub fn calculate_strategic_proof(
    meta_roas: f64, 
    verified_revenue: f64, 
    daily_spend: f64,
    sample_size: u32
) -> JsValue {
    // 1. Bayesian Reconciliation using Normal-Normal Conjugate Prior
    // Prior: Meta reported signals (The 'Belief')
    // Likelihood: Shopify verified revenue (The 'Evidence')
    
    let prior_mean = meta_roas;
    let prior_var = 0.5; // Estimated uncertainty in platform reporting
    
    let evidence_mean = verified_revenue / daily_spend.max(0.01);
    let evidence_var = 1.0 / (sample_size as f64).max(1.0); // Variance decreases as sample size grows
    
    // Bayesian Update: Posterior Mean = (Prior_Mean/Var + Evidence_Mean/Var) / (1/Var + 1/Var)
    let weight = (1.0 / evidence_var) / (1.0 / prior_var + 1.0 / evidence_var);
    let posterior_mean = (evidence_mean * weight) + (prior_mean * (1.0 - weight));
    let posterior_std = (1.0 / (1.0 / prior_var + 1.0 / evidence_var)).sqrt();
    
    let waste = daily_spend * (0f64.max(1.0 - (evidence_mean / meta_roas.max(0.1))));
    let n = Normal::new(posterior_mean, posterior_std.max(0.01)).unwrap();
    let p10 = n.inverse_cdf(0.10); // P10 Pessimistic Bound

    let result = BayesianResult {
        true_roas: (posterior_mean * 100.0).round() / 100.0,
        meta_roas,
        waste_usd: (waste * 100.0).round() / 100.0,
        p10_roas: (p10 * 100.0).round() / 100.0,
    };

    serde_wasm_bindgen::to_value(&result).unwrap()
}