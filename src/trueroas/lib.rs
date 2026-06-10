#![forbid(unsafe_code)]
use wasm_bindgen::prelude::*;

pub mod models;
pub mod vault;
pub mod api;
pub mod export;
pub mod self_defense;
pub mod referral;

use crate::vault::Vault;
use crate::models::{SensitiveString};
use anyhow::Result;
use zeroize::Zeroize;

#[wasm_bindgen]
pub fn run_analytics_web(
    email: String,
    store_id: String,
    hw_info: Vec<String>,
    meta_token: String,
    shopify_token: String,
) -> Result<String, String> {
    let mut m_token = SensitiveString::new(meta_token);
    let mut s_token = SensitiveString::new(shopify_token);

    let result = (|| -> Result<String> {
        // 1. Self-Defense Check
        self_defense::init(&email, &store_id)?;

        // 2. Open Vault (Note: Browser WASM relies on virtual FS or mock in this context)
        let vault = Vault::open(&email, hw_info)?;
        let _referral_id = referral::init(&vault)?;

        // 3. API Processing (In-memory)
        let meta_json = String::from("[]"); 
        let shopify_json = String::from("[]");
        api::ApiManager::process_meta_response(&vault, meta_json, &mut m_token)?;
        api::ApiManager::process_shopify_response(&vault, shopify_json, &mut s_token)?;

        // 4. Export
        let csv = export::ExportEngine::export_csv(&vault, email.clone())?;
        Ok(csv.to_string())
    })().map_err(|e| e.to_string());

    result
}

pub fn run_analytics_cycle(
    mut email: String,
    store_id: String,
    hw_info: Vec<String>,
    mut meta_token: SensitiveString,
    mut shopify_token: SensitiveString
) -> Result<()> {
    // 1. Self-Defense Init (Phase 2) – хамгийн түрүүнд
    self_defense::init(&email, &store_id)?;

    // 2. Hardware Binding + Encrypted Vault (Phase 1)
    let vault = Vault::open(&email, hw_info)?;

    // 3. Referral Identity (Phase 3) – vault нээгдсэний дараа
    let _referral_id = referral::init(&vault)?;

    // 4. API processing – memory-safe
    let meta_json = String::from("[]"); // production-д host fetch
    let shopify_json = String::from("[]");

    api::ApiManager::process_meta_response(&vault, meta_json, &mut meta_token)?;
    api::ApiManager::process_shopify_response(&vault, shopify_json, &mut shopify_token)?;

    // 5. Export with forensic watermark
    let csv = export::ExportEngine::export_csv(&vault, email.clone())?;
    std::fs::write("export.csv", csv.as_bytes())?;

    // 6. Dynamic pricing update
    let count = referral::get_count(&vault)?;
    let price = referral::monthly_price(count, vault.is_first_month());
    vault.store_pricing(price)?;

    // 7. PII wipe – заавал
    email.zeroize();
    Ok(())
}