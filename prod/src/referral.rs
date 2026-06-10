use crate::vault::Vault;
use anyhow::{Context, Result};
use sha2::{Sha256, Digest as ShaDigest};
use ed25519_dalek::{SigningKey, Signer, VerifyingKey, Signature, Verifier};
use serde::{Serialize, Deserialize};
use zeroize::Zeroize;
use wasm_bindgen::prelude::*;

// These constants are injected at build-time into identity_consts.rs
include!(concat!(env!("OUT_DIR"), "/identity_consts.rs"));

#[derive(Serialize, Deserialize)]
pub struct ReferralProof {
    pub referral_id: String,
    pub invite_count: u32,
    pub aggregated_hash: String,
    pub timestamp: i64,
    pub signature: Vec<u8>,
}

pub struct ReferralManager;

#[wasm_bindgen]
pub fn generate_payment_proof(email: &str, invites: u8) -> String {
    let mut hasher = Sha256::new();
    // SHA256(email_lowercase + ":" + invites + ":" + DEVICE_SALT)
    let data = format!("{}:{}:{}", email.to_lowercase(), invites, EMBEDDED_DEVICE_SALT);
    hasher.update(data.as_bytes());
    let hash = hasher.finalize();

    // EMBEDDED_PRIVATE_KEY is a master key for the system, protected by the Phase 2 kill-switch
    let signing_key = SigningKey::from_bytes(&EMBEDDED_SYSTEM_PRIVATE_KEY);
    let signature = signing_key.sign(&hash);
    hex::encode(signature.to_bytes())
}

#[wasm_bindgen]
pub fn verify_payment_proof(proof_hex: &str, email: &str, invites: u8, public_key_hex: &str) -> bool {
    let mut hasher = Sha256::new();
    let data = format!("{}:{}:{}", email.to_lowercase(), invites, EMBEDDED_DEVICE_SALT);
    hasher.update(data.as_bytes());
    let hash = hasher.finalize();

    let sig_bytes = hex::decode(proof_hex).unwrap_or_default();
    let pub_bytes = hex::decode(public_key_hex).unwrap_or_default();
    
    let signature = Signature::from_slice(&sig_bytes).unwrap();
    let verifying_key = VerifyingKey::from_slice(&pub_bytes.try_into().unwrap_or([0;32])).unwrap();

    verifying_key.verify(&hash, &signature).is_ok()
}

/// Initializes the referral identity and returns the referral_id.
pub fn init(vault: &Vault) -> Result<String> {
    ReferralManager::get_or_init_identity(vault)
}

/// Returns the current count of outbound referrals.
pub fn get_count(vault: &Vault) -> Result<u8> {
    let (_, count) = vault.get_all_outbound_referrals()?;
    Ok(count as u8)
}

/// Calculates the monthly price based on referral count.
pub fn monthly_price(count: u8, is_first_month: bool) -> u32 {
    ReferralManager::monthly_price(count, is_first_month)
}

impl ReferralManager {
    pub fn monthly_price(count: u8, is_first_month: bool) -> u32 {
        if is_first_month { return 149; }
        match count {
            5..=u8::MAX => 0,
            4 => 49,
            3 => 99,
            2 => 149,
            1 => 199,
            _ => 299,
        }
    }

    pub fn get_or_init_identity(vault: &Vault) -> Result<String> {
        let existing = vault.get_referral_key()?;
        let signing_key = match existing {
            Some(mut bytes) => {
                let key = SigningKey::from_bytes(bytes.as_slice().try_into().context("Invalid key")?);
                bytes.zeroize();
                key
            }
            None => {
                let mut seed = [0u8; 32];
                getrandom::getrandom(&mut seed)?;
                let key = SigningKey::from_bytes(&seed);
                vault.set_referral_key(&seed)?;
                seed.zeroize();
                key
            }
        };
        let verifying_key: VerifyingKey = signing_key.verifying_key();
        Ok(bs58::encode(&verifying_key.to_bytes()).into_string()[..8].to_string())
    }

    pub fn record_invite(vault: &Vault, email: &str) -> Result<()> {
        if let Ok(inviter_id) = std::env::var("INVITED_BY") {
            let mut key_bytes = vault.get_referral_key()?.context("Identity missing")?;
            let signing_key = SigningKey::from_bytes(key_bytes.as_slice().try_into().unwrap());
            
            let mut hasher = Blake2b512::new();
            hasher.update(email.as_bytes());
            let my_hash = hasher.finalize().to_vec();
            
            let signature = signing_key.sign(&my_hash).to_bytes().to_vec();
            vault.store_referral_outbound(&inviter_id, signature, my_hash)?;
            key_bytes.zeroize();
        }
        Ok(())
    }

    pub fn generate_proof(vault: &Vault) -> Result<String> {
        let (invites, count) = vault.get_all_outbound_referrals()?;
        let referral_id = Self::get_or_init_identity(vault)?;
        
        let mut signatures: Vec<Vec<u8>> = invites.into_iter().map(|i| i.1).collect();
        signatures.sort();
        
        let mut agg_hasher = Blake2b512::new();
        // Ensure deterministic ordering and separator to prevent concatenation attacks
        for sig in &signatures { 
            agg_hasher.update(sig);
            agg_hasher.update(b"|"); 
        }
        let aggregated_hash = hex::encode(agg_hasher.finalize());

        let timestamp = chrono::Utc::now().timestamp();
        let proof_data = format!("{}|{}|{}|{}", referral_id, count, aggregated_hash, timestamp);
        
        let mut key_bytes = vault.get_referral_key()?.context("Identity missing")?;
        let signing_key = SigningKey::from_bytes(key_bytes.as_slice().try_into().unwrap());
        let signature = signing_key.sign(proof_data.as_bytes()).to_bytes().to_vec();
        key_bytes.zeroize();

        let proof = ReferralProof {
            referral_id,
            invite_count: count as u32,
            aggregated_hash,
            timestamp,
            signature,
        };

        let json = serde_json::to_string(&proof)?;
        proof_data.zeroize();
        Ok(base64::encode(json))
    }
}