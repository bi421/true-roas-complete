use serde::{Deserialize, Serialize};
use zeroize::Zeroize;

/// Sensitive string wrapper that automatically zeroizes memory when dropped.
#[derive(Serialize, Deserialize, Zeroize, Debug)]
#[zeroize(drop)]
pub struct SensitiveString(String);

impl SensitiveString {
    pub fn new(s: String) -> Self {
        Self(s)
    }
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Serialize, Deserialize, Zeroize)]
#[zeroize(drop)]
pub struct MetaAdData {
    pub campaign_id: String,
    pub spend: f64,
    pub impressions: u64,
    pub timestamp: String,
}

#[derive(Serialize, Deserialize, Zeroize)]
#[zeroize(drop)]
pub struct ShopifyOrderData {
    pub order_id: String,
    pub revenue: f64,
    pub currency: String,
    pub timestamp: String,
}

#[derive(Serialize, Deserialize, Zeroize)]
#[zeroize(drop)]
pub struct RoasCalculation {
    pub date: String,
    pub total_spend: f64,
    pub total_revenue: f64,
    pub true_roas: f64,
}

/// Data structure for the export watermark.
pub struct ForensicWatermark {
    pub email: String,
    pub timestamp: i64,
}

impl Zeroize for ForensicWatermark {
    fn zeroize(&mut self) { self.email.zeroize(); }
}