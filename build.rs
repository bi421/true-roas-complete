use blake2::{Blake2b512, Digest};
use std::env;
use std::fs;
use std::path::Path;
use chrono::Utc;

fn main() {
    // 1. Personalized Identity Anchor
    let email = env::var("USER_EMAIL").unwrap_or_else(|_| "dev@trueroas.local".to_string());
    let store_id = env::var("SHOPIFY_STORE_ID").unwrap_or_else(|_| "dev-store".to_string());
    let referral_id = env::var("REFERRAL_ID").unwrap_or_else(|_| "00000000".to_string());
    let is_founder = env::var("FOUNDER").map(|v| v == "true").unwrap_or(false);

    let mut hasher = Blake2b512::new();
    hasher.update(format!("{}|{}", email, store_id).as_bytes());
    let intermediate_hash = hasher.finalize();

    let mut final_hasher = Blake2b512::new();
    final_hasher.update(&intermediate_hash);
    final_hasher.update(referral_id.as_bytes());
    let final_user_hash = final_hasher.finalize();

    // 2. Time Bomb logic
    let compile_date = Utc::now();
    let expiry_ts = if is_founder {
        2099 * 365 * 24 * 3600 // Roughly 2099
    } else {
        compile_date.timestamp() + (365 * 24 * 3600)
    };

    // 3. Emit constants to a generated file
    let out_dir = env::var_os("OUT_DIR").unwrap();
    let dest_path = Path::new(&out_dir).join("identity_consts.rs");

    let const_data = format!(
        "pub const EMBEDDED_USER_HASH: [u8; 64] = {:?};\n\
         pub const EMBEDDED_REFERRAL_ID: &str = \"{}\";\n\
         pub const BUILD_EXPIRY_TS: i64 = {};\n",
        final_user_hash.as_slice(),
        referral_id,
        expiry_ts
    );

    fs::write(dest_path, const_data).unwrap();
    println!("cargo:rerun-if-env-changed=USER_EMAIL");
    println!("cargo:rerun-if-env-changed=SHOPIFY_STORE_ID");
}