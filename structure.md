# TrueROAS File Manifest & Technical Stack

This document details the production-grade file tree and technology stack for the TrueROAS platform.

*Updated: 2026-06-03*
---

## 1. Project Structure

```text
src/trueroas/               # Root of the application logic
├── main.py                 # FastAPI application entry point
├── api/
│   ├── dependencies.py     # Auth & Tenant resolution
│   ├── limiter.py          # API Rate limiting
│   └── routes/
│       ├── health.py       # Heartbeats & Readiness
│       ├── sync.py         # Data ingest triggers & task polling
│       ├── analysis.py     # Metrics & audit snapshots
│       ├── reports.py      # PDF report status & downloads
│       └── webhooks.py     # Shopify real-time order events
├── core/
│   ├── config.py           # Pydantic settings & mathematical thresholds
│   ├── database.py         # SQLite/Postgres abstraction, tenant isolation
│   ├── migrations.py       # Tenant-specific schema versioning
│   ├── inference.py        # Bayesian + Bootstrap statistical core
│   ├── decision_intelligence.py # Decision engine logic
│   └── constants.py        # Centralized business logic constants
├── services/
│   ├── pdf_service.py      # Async PDF generation using WeasyPrint
│   └── security.py         # Path validation & per-tenant PII hashing
├── workers/
│   ├── tasks.py            # Celery background task definitions
│   └── celery_app.py       # Distributed task worker config
└── decision/
    ├── recommendation_engine.py
    └── accountability.py
tests/
├── unit/                   # Statistical & logic unit tests
├── integration/            # API contract & multi-tenancy tests
└── property/               # Hypothesis-based math invariant tests
docker-compose.yml
.env.example
```

---

## 2. Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | FastAPI + Uvicorn | Async API, OpenAPI documentation |
| Database | SQLite (per-tenant) or Postgres | WAL mode concurrency, isolated persistence |
| Task Queue | Celery + Redis | Non-blocking data sync, async PDF generation |
| Statistics | SciPy + Bootstrap | Bayesian conjugate priors, non-parametric fallback |
| Validation | Pydantic v2 | Strict request/response modeling & settings |
| Testing | pytest + Hypothesis | Unit, integration, and property-based testing |
| PDF | WeasyPrint | Professional reporting (worker-process execution) |
| Security | BLAKE2b + HMAC | Isolated per-tenant PII salting & hashing |

---
*Documentation updated: 2024-06-01*
**Precision over vanity. Evidence over assumptions. Decisions over dashboards.**