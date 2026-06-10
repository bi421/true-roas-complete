use crate::models::{SensitiveString, MetaAdData, ShopifyOrderData};
use crate::vault::Vault;
use anyhow::Result;
use zeroize::Zeroize;

/// Simulates the user-initiated fetch from Meta/Shopify APIs.
/// In WASM, the actual networking is performed by the host environment or a permitted fetch call.
pub struct ApiManager;

impl ApiManager {
    /// Processes raw Meta API response in RAM, encrypts to vault, and wipes.
    pub fn process_meta_response(vault: &Vault, mut raw_response: String, token: &mut SensitiveString) -> Result<()> {
        let result = (|| -> Result<()> {
            let ads: Vec<MetaAdData> = serde_json::from_str(&raw_response)?;
            for ad in ads {
                vault.store_data("meta_ads", &serde_json::to_string(&ad)?)?;
            }
            Ok(())
        })();

        // 3. Proactive Wipe
        raw_response.zeroize();
        token.zeroize();
        result
    }

    /// Processes raw Shopify API response in RAM, encrypts to vault, and wipes.
    pub fn process_shopify_response(vault: &Vault, mut raw_response: String, token: &mut SensitiveString) -> Result<()> {
        let result = (|| -> Result<()> {
            let orders: Vec<ShopifyOrderData> = serde_json::from_str(&raw_response)?;
            for order in orders {
                vault.store_data("shopify_orders", &serde_json::to_string(&order)?)?;
            }
            Ok(())
        })();

        raw_response.zeroize();
        token.zeroize();
        result
    }
}

impl Zeroize for ApiManager {
    fn zeroize(&mut self) {
        // Stateless
    }
}