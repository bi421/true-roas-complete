use crate::models::SensitiveString;
use anyhow::{Context, Result};
use blake2::{digest::consts::U32, Blake2b, Digest};
use pbkdf2::pbkdf2_hmac;
use rusqlite::Connection;
use sha2::Sha256;
use zeroize::Zeroize;
use std::fs;

pub struct Vault {
    conn: Connection,
}

impl Vault {
    /// Initializes the encrypted SQLite vault with SQLCipher verification.
    pub fn open(email: &str, mut hw_info: Vec<String>) -> Result<Self> {
        let mut key = Self::derive_key(email, &mut hw_info)?;
        
        let mut vault_dir = dirs::home_dir().context("Could not find home directory")?;
        vault_dir.push(".trueroas");
        fs::create_dir_all(&vault_dir).context("Failed to create vault directory")?;
        let db_path = vault_dir.join("vault.db");

        let conn = Connection::open(&db_path).context("Failed to open vault")?;
        
        // SQLCipher Encryption
        let pragma_key = format!("PRAGMA key = \"x'{}'\";", hex::encode(key));
        conn.execute_batch(&pragma_key)?;
        
        // SQLCipher Verification: Ensure the engine is active and the vault is encrypted
        let _: String = conn.query_row("PRAGMA cipher_version;", [], |r| r.get(0))
            .context("SQLCipher not active – vault is not encrypted")?;

        // Immediately wipe the key from memory
        key.zeroize();

        let vault = Self { conn };
        vault.init_tables()?;
        
        Ok(vault)
    }

    /// Derives a 32-byte key using PBKDF2-HMAC-SHA256.
    fn derive_key(email: &str, hw_info: &mut Vec<String>) -> Result<[u8; 32]> {
        let fingerprint = Self::generate_fingerprint(hw_info);
        let mut key = [0u8; 32];
        let salt = email.as_bytes();

        pbkdf2_hmac::<Sha256>(
            &fingerprint,
            salt,
            600_000,
            &mut key,
        );

        Ok(key)
    }

    /// Generates a hardware fingerprint using BLAKE2b (32-byte).
    fn generate_fingerprint(hw_info: &mut Vec<String>) -> [u8; 32] {
        let mut hasher = Blake2b::<U32>::new();
        for info in hw_info.iter_mut() {
            hasher.update(info.as_bytes());
            info.zeroize(); // Clear raw info
        }
        let mut result = [0u8; 32];
        result.copy_from_slice(&hasher.finalize());
        result
    }

    fn init_tables(&self) -> Result<()> {
        self.conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS meta_ads (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS shopify_orders (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS calculations (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sys_keys (
                key_name TEXT PRIMARY KEY,
                val BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS referrals_outbound (
                inviter_id TEXT,
                signature BLOB,
                my_hash BLOB,
                created_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS referrals_inbound_count (
                count INTEGER,
                last_proof TEXT
            );"
        )?;
        Ok(())
    }

    pub fn get_referral_key(&self) -> Result<Option<Vec<u8>>> {
        self.conn.query_row("SELECT val FROM sys_keys WHERE key_name = 'referral_private'", [], |r| r.get(0)).optional().map_err(Into::into)
    }

    pub fn set_referral_key(&self, bytes: &[u8; 32]) -> Result<()> {
        self.conn.execute("INSERT OR REPLACE INTO sys_keys (key_name, val) VALUES ('referral_private', ?)", [bytes.as_slice()])?;
        Ok(())
    }

    pub fn store_referral_outbound(&self, inviter: &str, sig: Vec<u8>, hash: Vec<u8>) -> Result<()> {
        self.conn.execute("INSERT INTO referrals_outbound (inviter_id, signature, my_hash, created_at) VALUES (?, ?, ?, ?)", (inviter, sig, hash, chrono::Utc::now().timestamp()))?;
        Ok(())
    }

    pub fn get_all_outbound_referrals(&self) -> Result<(Vec<(String, Vec<u8>, Vec<u8>)>, usize)> {
        let mut stmt = self.conn.prepare("SELECT inviter_id, signature, my_hash FROM referrals_outbound")?;
        let rows = stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?;
        let mut results = Vec::new();
        for r in rows { results.push(r?); }
        let count = results.len();
        Ok((results, count))
    }

    /// Encrypts and stores a JSON payload.
    pub fn store_data(&self, table: &str, payload: &str) -> Result<()> {
        let query = format!("INSERT INTO {} (data) VALUES (?)", table);
        self.conn.execute(&query, [payload])?;
        Ok(())
    }

    /// Retrieves all records as SensitiveString.
    pub fn fetch_all(&self, table: &str) -> Result<Vec<SensitiveString>> {
        let mut stmt = self.conn.prepare(&format!("SELECT data FROM {}", table))?;
        let rows = stmt.query_map([], |row| {
            let data: String = row.get(0)?;
            Ok(SensitiveString::new(data))
        })?;
        
        let mut results = Vec::new();
        for row in rows {
            results.push(row?);
        }
        Ok(results)
    }

    /// Checks if this is the first month of operation (no calculations stored).
    pub fn is_first_month(&self) -> bool {
        let count: i64 = self.conn
            .query_row("SELECT COUNT(*) FROM calculations", [], |r| r.get(0))
            .unwrap_or(0);
        count == 0
    }

    /// Stores the calculated monthly price in the system keys.
    pub fn store_pricing(&self, price: u32) -> Result<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO sys_keys (key_name, val) VALUES ('current_price', ?)",
            [price.to_string().as_bytes()],
        )?;
        Ok(())
    }
    
    pub fn get_connection(&self) -> &Connection {
        &self.conn
    }
}