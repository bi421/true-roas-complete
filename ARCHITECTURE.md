# TrueROAS System Architecture

This document details the technical structure, data processing, and multi-tenant isolation logic of the platform.

---

## 1. High-Level Architecture

```mermaid
graph TD
    subgraph External_APIs [External APIs]
        M[Meta Graph API]
        S[Shopify Admin API]
    end

    subgraph Worker_Layer [Data Collection - Workers]
        MS[meta_sync.py]
        SS[shopify_sync.py]
        RD[reconcile_decisions.py]
    end

    subgraph Data_Layer [Data Layer - Storage]
        DB[(DuckDB Multi-tenant Warehouse)]
        MG[migrations.py]
    end

    subgraph Logic_Layer [Decision Brain]
        INF[inference.py - Bayesian & SciPy]
        DI[decision_intelligence.py - Risk/Ready/Eco Engines]
        ACC[accountability.py - Accuracy Tracking]
    end

    subgraph API_Interface [User Interface]
        Main[main.py - FastAPI Server]
        Dash[HTML/JS Dashboard]
        PDF[Strategy PDF Export]
    end

    M --> MS
    S --> SS
    MS & SS --> DB
    DB --> Logic_Layer
    Logic_Layer --> API_Interface
    RD --> DB
    MG --> DB
```

---

## 2. Multi-Tenancy & Data Isolation
TrueROAS uses a **Silo Isolation Pattern** for maximum security:
- **Storage:** Each account has a dedicated `.duckdb` file located in `data/tenants/{tenant_id}/warehouse.duckdb`.
- **Encryption:** PII (Personally Identifiable Information) is never stored raw. We use salted BLAKE2b hashing for all customer identifiers.
- **Path Security:** Tenant IDs are sanitized to prevent directory traversal attacks.

---

## 3. Stakeholder Control Loop

```mermaid
sequenceDiagram
    participant A as Accountant
    participant R as Risk Manager
    participant M as Marketing Manager
    participant C as CEO

    A->>Logic: Set VARIABLE_COST
    Note over A,Logic: Monitor Attribution Variance
    
    R->>Logic: Match Rate & Confidence Audit
    Note over R,Logic: Monitor system errors (MAE/Bias)
    
    M->>Logic: Bottleneck (CTR/CR) Diagnosis
    Note over M,Logic: Implement Action Plan
    
    C->>Logic: EV & Delay Cost Monitoring
    Note over C,Logic: Authorize budget increase decision
```