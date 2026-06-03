# TrueROAS System Architecture

This document details the technical structure, data processing, and multi-tenant isolation logic of the platform.

*Updated: 2026-06-03*
---

## 0. Системийн ажиллах үндсэн зарчим (Working Principle)

TrueROAS нь маркетингийн платформуудын (Meta, Google) мэдээлдэг хэтрүүлэгтэй датаг бодит борлуулалттай (Shopify) харьцуулан "Үнэний шүүлтүүр" (Bayesian Filter) ашиглан боловсруулдаг.

```mermaid
flowchart LR
    subgraph Inputs [Түүхий өгөгдөл]
        M[Meta: 4.0 ROAS]
        S[Shopify: Бодит борлуулалт]
    end

    subgraph Engine [TrueROAS Тархи]
        B{Bayesian Filter}
        B --> |Шүүлтүүр| R[Readiness Audit]
        R --> |Шинжилгээ| E[Economic Projection]
    end

    subgraph Output [Гарах үр дүн]
        V[Verified Truth: 2.8 ROAS]
        A[Action: SCALE эсвэл HOLD]
    end

    Inputs --> Engine --> Output
```

---
## 1. High-Level Architecture

```mermaid
graph TD
    subgraph External_APIs [External APIs]
        M[Meta Graph API]
        S[Shopify Admin API]
        W[Shopify Webhooks]
    end

    subgraph API_Interface [API Layer]
        Main[FastAPI Server]
        RB[Redis Task Broker]
    end

    subgraph Worker_Layer [Celery Workers]
        MS[meta_sync]
        SS[shopify_sync]
        PG[pdf_generator]
        RD[reconcile_decisions]
    end

    subgraph Data_Layer [Storage & Persistence]
        DB[(SQLite/PostgreSQL Tenant-Isolated)]
        S3[S3/Local Storage - PDF Reports]
        MG[migrations.py]
    end

    subgraph Logic_Layer [Decision Brain]
        INF[inference.py - Bayesian & SciPy]
        DI[decision_intelligence.py - Risk/Ready/Eco Engines]
        ACC[accountability.py - Accuracy Tracking]
    end

    W -- Event Driven --> Main
    Main -- Async Task --> RB
    RB -- Claim Task --> MS & SS & PG & RD
    M -- Graph Response --> MS
    S -- Admin Response --> SS
    MS & SS -- Write Isolated --> DB
    PG -- Write Report --> S3
    RD -- Reconcile --> DB
    DB --> Logic_Layer
    Logic_Layer --> Main
    MG --> DB
```

---

## 2. Multi-Tenancy & Data Isolation
TrueROAS uses a **Silo Isolation Pattern** for maximum security:
- **Storage:** Each account has a dedicated SQLite file located in `data/tenants/{tenant_id}/warehouse.db`.
- **No Central Cloud:** There is no "TrueROAS Cloud". The database is a local file on your hardware.
- **Zero External Outbound:** The application only communicates with Meta and Shopify APIs. It never sends usage reports or business data to any third party.
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