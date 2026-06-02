# TrueROAS System Structure & Logic

This document illustrates the technical structure, data processing, and 11-step decision-making logic of the TrueROAS Decision Accountability platform.

---

## 1. High-Level Architecture

TrueROAS consists of four main layers: data collection, processing, diagnosis, and delivery to the user.

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

## 2. Decision Logic Flow

The process of integrating Bayesian probability and economic calculations into "Strategic Advice."

```mermaid
flowchart LR
    A[Raw Data: Meta vs Shopify] --> B{Bayesian Reconciliation}
    B --> C[Posterior ROAS & Std Dev]
    
    subgraph Intelligence_Engines [Intelligence Engines]
        direction TB
        E1[Quality Engine: Trust Score]
        E2[Readiness Engine: Bottleneck Diagnosis]
        E3[Economic Engine: Cost of Loss]
    end

    C --> Intelligence_Engines
    Intelligence_Engines --> D[Expected Value Calculation]
    D --> E[Recommendation Engine]
    E --> F[11-Step Reasoning Order Output]
```

---

## 3. Stakeholder Control Loop

How the four key roles interact with the system to derive value as outlined in the documentation.

```mermaid
sequenceDiagram
    participant A as Accountant
    participant R as Risk Manager
    participant M as Marketing Manager
    participant C as CEO

    A->>Logic: Set VARIABLE_COST
    Note over A,Logic: Monitor Attribution Variance
    
    R->>Logic: Match Rate & Confidence Audit
    Note over R,Logic: Monitor System Error (MAE/Bias)
    
    M->>Logic: Bottleneck (CTR/CR) Diagnosis
    Note over M,Logic: Implement Action Plan
    
    C->>Logic: EV & Delay Cost Monitoring
    Note over C,Logic: Confirm Budget Decision
```

---

## 4. File Structure (File Manifest)

*   `main.py`: Central control, API endpoints, and Dashboard.
*   `src/trueroas/core/inference.py`: Statistical calculation core (SciPy/Bayesian).
*   `src/trueroas/core/decision_intelligence.py`: Business logic modules.
*   `src/trueroas/core/migrations.py`: Database schema and automation.
*   `src/trueroas/workers/`: Data ingestion and reconciliation (Sync/Reconcile).
*   `src/trueroas/decision/accountability.py`: System self-error tracking loop.

---
*Documentation updated: 2024-05-31*
**Precision over vanity. Evidence over assumptions. Decisions over dashboards.**