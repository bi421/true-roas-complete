# TrueROAS Zero-Touch Self-Learning System

## Overview
The Learning System adapts strategic thresholds based on the accuracy of past predictions. It utilizes a Bayesian feedback loop to correct systematic bias and minimize Brier Scores.

## Architectural Flow (Zero-Knowledge)

The following diagram illustrates the flow from the Data Plane (Worker) to the Control Plane.

```mermaid
sequenceDiagram
    participant Worker as Data Plane (Celery Worker)
    participant DB as Tenant Storage (DuckDB/Postgres)
    participant Tuner as AutoTuner (Bayesian Logic)
    participant API as Control Plane (Proof Ingestion)

    Note over Worker: reconcile_decisions Task Finishes
    Worker->>Tuner: Trigger learning_hook (Celery Signal)
    Tuner->>DB: Read Technical Aggregates (No PII)
    DB-->>Tuner: ROAS predictions, outcomes, confidence
    Tuner->>Tuner: Calculate Brier Score & Systematic Bias
    Tuner->>Tuner: Compute Deterministic Threshold Delta
    Tuner->>Tuner: Canonicalize & Sign (HMAC-SHA256)
    Tuner->>API: POST /api/v1/proofs (Signed Policy Update)
    API->>DB: Append to WORM Audit Trail
```

## Security & Compliance
- **Zero-Knowledge:** The `PolicyStore` only retrieves `expected_roas`, `confidence`, and `actual_outcome`. It explicitly ignores `assumptions_json` or customer-related metadata.
- **WORM Compliance:** Every threshold adjustment is treated as a "Strategic Proof," signed on the worker and verified on the server.
- **Determinism:** The Bayesian update is deterministic, allowing auditors to replay the learning cycle from historical data to verify the resulting threshold was valid.

## Configuration
Toggled via `.env`:
- `LEARNING_ENABLED`: (bool) Enables the system.
- `LEARNING_MIN_SAMPLES`: (int) Minimum reconciled decisions required before tuning occurs.

## Migrations
Initialize the learning infrastructure:
```bash
python -m src.trueroas.learning.migrate
```