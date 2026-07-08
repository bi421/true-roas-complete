## TrueROAS – Zero-Knowledge ROAS Engine

### The Problem
Modern advertising platforms provide performance metrics that frequently diverge from actual financial outcomes. Traditional third-party analytics solutions address this by centralizing sensitive customer PII and order data, creating significant data liability and sovereignty risks for e-commerce brands.

### Our Architecture (Local-First)
TrueROAS utilizes a local-first, zero-knowledge architecture. All computation occurs at the edge within a restricted WebAssembly (WASM) environment. By moving the data plane to the client's local infrastructure, raw Shopify orders and Meta Ads spend data never egress from the user's environment.

The server-side Control Plane performs threshold tuning in pure Python (`src/trueroas/learning/auto_tuner.py`, `AutoTuner.compute_new_threshold`), using Brier score with sample-size dampening; it does not call a WASM learning core via wasmer.

### Phase 1: User Data Protection
We cannot see your data. Ever. All sensitive information is stored in an encrypted vault located at `~/.trueroas/vault.db`. 

*   **At-Rest Encryption:** The vault uses SQLCipher with AES-256-CBC.
*   **Key Derivation:** We utilize PBKDF2-HMAC-SHA256 with 600,000 iterations. The salt is derived from the user's email, and the password is bound to a unique hardware fingerprint (CPU ID and OS version).
*   **Memory Hygiene:** The `zeroize` crate is used to overwrite sensitive heap buffers on all execution paths, including error states, ensuring secrets do not persist in RAM.

### Phase 2: Code Self-Defense
TrueROAS is a tamper-reactive binary. Each build is personalized and cryptographically bound to the authorized user.

*   **Personalized Build:** A unique `USER_HASH` is embedded into the binary at compile time.
*   **Integrity Kill Switch:** On startup, the engine performs a BLAKE2b-512 integrity check of its own bytecode.
*   **Tamper Deterrent:** If tampering or a license mismatch is detected, the binary executes a self-wipe of the first 1MB of its executable.
*   **Data Poisoning:** Unauthorized instances activate a poisoning routine that corrupts ROAS output by 50%, introducing randomized noise to prevent the use of stolen analytics.

### Phase 3: Serverless Referral System
The referral system operates without a central database, preserving the sovereign nature of the application.

*   **Identity Generation:** Each user generates an ed25519 keypair locally. The `referral_id` is derived from the base58-encoded public key.
*   **Aggregated Proofs:** Referrals are verified via aggregated zero-knowledge proofs. No PII of invitees is transmitted; only signed cryptographic commitments are sent to Stripe metadata during the checkout process.
*   **Dynamic Pricing:** The system calculates pricing tiers ($299 to $0) locally based on verifiable signatures stored in the vault.

### License & Anti-Tampering
TrueROAS is closed-source, personal-use software.

**You MAY:**
*   Use on your own Shopify stores.
*   Build your own dashboard on top of the exported data.

**You MAY NOT:**
*   Copy, resell, or distribute the binary.
*   Modify, reverse-engineer, or remove the forensic watermark.
*   Share your personalized build.

**Protection:** Each build is cryptographically bound to your email + store ID. The binary self-checks its integrity on startup (BLAKE2b). Tampering violates the license and will result in permanent ban from updates and the Founders Club. We do not use servers – the protection is built into the code itself.

© 2026 TrueROAS. All rights reserved.

### Security Guarantees

| Guarantee | Verification |
| :--- | :--- |
| **No Data Exfiltration** | Post-initialization, the binary lacks network syscalls in the WASI runtime. |
| **No Telemetry** | Source audit confirms zero tracking SDK or analytic endpoint dependencies. |
| **Hardware-Bound Encryption** | PBKDF2 key derivation binds the vault to the local hardware fingerprint. |
| **Memory Hygiene** | Secrets implement `ZeroizeOnDrop` to overwrite heap buffers upon deallocation. |
| **Verifiable Builds** | Personalization anchors builds to unique user salts, preventing binary sharing. |

### Technical Specifications
*   **Language:** Rust 1.75+
*   **Target:** `wasm32-wasi`
*   **Safety:** `#![forbid(unsafe_code)]` enforced across all modules.
*   **Dependencies:** `rusqlite` (sqlcipher), `zeroize`, `blake2`, `ed25519-dalek`.
*   **Binary Footprint:** < 5MB.

### Installation
TrueROAS provides automated build scripts to simplify the personalization process:

*   **Windows:** Double-click `build_windows.bat`.
*   **macOS/Linux:** Run `bash build_macos.sh` in your terminal.

These scripts ensure Rust is installed, prompt for your credentials, and compile your personalized WASM binary.

### Verification (How to Audit Us)

**Dependency Audit**
Verify the exclusion of network-capable dependencies and security vulnerabilities:
```bash
cargo audit
```

**Vault Encryption**
Verify that the local database is encrypted and running SQLCipher:
```bash
sqlite3 ~/.trueroas/vault.db "PRAGMA cipher_version;"
```

**Memory Inspection**
Search for unencrypted PII or secret strings in the compiled WASM binary:
```bash
strings target/wasm32-wasi/release/trueroas.wasm | grep -i "secret"
```

**Tamper Detection Test**
Manually modify the binary to trigger the integrity protection:
```bash
echo "tamper" >> target/wasm32-wasi/release/trueroas.wasm
# Execute binary to confirm self-wipe/exit
```
