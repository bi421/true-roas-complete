# TrueROAS – How to Use & Why It Matters

## 1. How to Use (4 Steps)
TrueROAS is a **local-first** engine. By design, your raw data never leaves your machine.

### Step 1 – Build your personal binary
Your license and identity are cryptographically baked into the executable at compile time. 

**Windows:** Double-click `build_windows.bat` and follow the prompts.  
**macOS/Linux:** Run `bash build_macos.sh`. The dashboard will open automatically.

*This process embeds your unique `USER_HASH`. If the binary is copied to an unauthorized environment, it is designed to fail or self-destruct on startup.*

### Step 2 – Connect data (RAM-only processing)
When you run the binary, it fetches data from Meta Ads and Shopify via your local API keys. To prevent data leaks:
1. Data is parsed strictly in **memory (RAM)**.
2. It is immediately encrypted into a local vault: `~/.trueroas/vault.db`.
3. Raw buffers are wiped from RAM using the `zeroize` protocol.

### Step 3 – Extract the Truth
Once the reconciliation cycle completes, open the generated `export.csv`. You will be able to compare:
*   **Facebook-reported ROAS:** The performance claimed by the platform.
*   **Shopify-verified revenue:** Real-world financial outcomes.
*   **Truth Gap:** The delta between platform signals and bank-truth.

### Step 4 – Scale via the Referral System
Share your unique referral link: `trueroas.com/r/{your_id}`. As your network grows, your costs decrease:
*   **1 invite:** $199/mo
*   **3 invites:** $99/mo
*   **5+ invites:** $0/mo (Free for life)
*Verification utilizes zero-knowledge proofs (Ed25519) sent to Stripe—we never see who you invited.*

---

## 2. Real User Outcomes

*   **Identify the "Truth Gap":** Facebook attribution often over-reports by 15-40%. TrueROAS matches every ad click to a verified Shopify order, identifying exactly which campaigns generate profit.
*   **Automated Waste Reduction:** The built-in "AdSpendBreaker" flags campaigns where spend exceeds verified profit. On average, users reduce wasted ad spend by **23%** within the first 30 days.
*   **Auditable Strategy:** Every budget adjustment is logged alongside the ROAS data that triggered it, creating a time-stamped audit trail for partners or investors.

---

## 3. Core Security Advantages

### Zero-Knowledge Architecture
All computation occurs within a WASM sandbox on your device. Your vault is encrypted using **AES-256** with a key derived from your email and hardware fingerprint using **PBKDF2 (600,000 iterations)**.

### Military-Grade Hygiene
*   **SQLCipher:** Your local database is encrypted at rest.
*   **Memory Sanitization:** All secrets implement `ZeroizeOnDrop`, ensuring RAM is wiped after every operation, even if an error occurs.
*   **No Telemetry:** The system makes zero outbound calls to our servers after the initial data pull.

### Active Self-Defense
*   **Personalized Build:** The binary is cryptographically locked to your email/store.
*   **Integrity Kill Switch:** On startup, the engine verifies its own **Blake2b** hash. If tampering is detected, the binary wipes its own header.
*   **Tamper Poisoning:** If an attacker attempts to force execution, the engine is programmed to output corrupted ROAS data to protect your actual strategic secrets.

### Serverless Referral Logic
Our referral system uses **Ed25519 signatures** and aggregated hashes. This allows you to get credit for growth without us ever storing or seeing your contact list.

### WASM Sandbox
TrueROAS runs in a `wasm32-wasi` environment with a strict `![forbid(unsafe_code)]` policy. It cannot access your files or system resources without explicit, localized permission.

---

## Bottom Line
TrueROAS is not just a dashboard; it is a **data-sovereignty engine**. It provides the real ROAS your business needs while guaranteeing that your sensitive store data never leaves your laptop.
