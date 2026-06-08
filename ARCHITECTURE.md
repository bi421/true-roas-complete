# TrueROAS Systems Architecture: Zero-Knowledge Model

TrueROAS utilizes a strictly decoupled architecture that separates the **Control Plane** (Cloud Orchestrator) from the **Data Plane** (Client-Side Compute).

## 1. Architectural Philosophy

Traditional SaaS models require "Data Egress" where sensitive raw orders and PII are uploaded to a vendor's server. TrueROAS eliminates this vulnerability. The Data Plane performs the heavy lift of data ingestion and Bayesian math locally. It then transmits a "Strategic Proof"—a highly compressed JSON object containing only calculated metrics and a cryptographic signature—to the Control Plane.

## 2. Process Flow

```mermaid
sequenceDiagram
    participant Local_Agent as Data Plane (In-Browser WASM)
    participant Raw_Data as Raw Sources (Shopify/Meta)
    participant Control_Plane as Control Plane (TrueROAS Server)
    participant Dashboard as User Dashboard

    Local_Agent->>Control_Plane: POST /api/v1/leads (onboarding)
    Control_Plane-->>Local_Agent: {tenant_id, app_salt}

    Note over Local_Agent, Raw_Data: No Cloud Egress of Raw Data
    Local_Agent->>Raw_Data: Pull Ad Spend & Revenue Records
    Local_Agent->>Local_Agent: Bayesian Reconciliation (Rust WASM Compute)
    Local_Agent->>Local_Agent: Sign Metrics with HMAC-SHA256
    
    Local_Agent->>Control_Plane: POST /api/v1/proofs {Metrics, Signature}
    Control_Plane->>Control_Plane: Verify Signature via Shared Secret
    Control_Plane->>Control_Plane: Archive Verified Proof (DuckDB)
    
    Dashboard->>Control_Plane: GET /api/v1/cfo/dashboard
    Control_Plane-->>Dashboard: Return Actionable Strategy
```

## 3. The Proof Interface (/api/v1/proofs)

The Control Plane exposes a high-integrity endpoint for the Data Plane to submit results.

**Payload Structure:**
```json
{
  "true_roas": 2.8,
  "meta_roas": 4.2,
  "daily_spend": 1200.50,
  "waste_usd": 480.20,
  "capital_health": "WARNING",
  "action_required": "REDUCE_OR_HOLD",
  "cfo_brief": "Variance exceeds 30%. Stop scaling immediately.",
  "signature": "7f83... (HMAC-SHA256)"
}
```

## 4. Security Enforcement

1. **Shared Secret:** Every tenant is provisioned with a unique application salt during onboarding.
2. **HMAC Integrity:** The Control Plane re-computes the signature using the received JSON body and the stored secret. If they do not match, the proof is rejected.
3. **Local Sovereignty:** The `src/trueroas/main.py` entry point contains no logic for reading Shopify order tables. It is physically impossible for the server to access raw data.

---
*Proprietary and Confidential. TrueROAS Team 2024.*