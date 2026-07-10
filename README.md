# TrueROAS – Decision Intelligence & ROAS Reconciliation Platform

## The Problem
Meta Ads ROAS reporting consistently diverges from verified financial outcomes. Traditional analytics tools compensate by centralizing sensitive Shopify PII and ad spend data, creating data liability and sovereignty risks for DTC brands.

TrueROAS reconciles platform-reported ROAS against verified revenue using a local-first, zero-knowledge architecture where raw financial data never leaves the tenant's infrastructure.

## Current Architecture (FastAPI + PostgreSQL/DuckDB)

### Control Plane (`src/trueroas/main.py`)
- **Framework:** FastAPI 2.x with async lifespan management
- **Port:** 10000 (configurable via `PORT` env var)
- **Database:** PostgreSQL 15 (central: leads, ZK proofs, subscriptions) + DuckDB (tenant warehouses)
- **Task Queue:** Celery + Redis (high/medium/low priority queues)
- **Security:** HMAC-SHA256 proof signatures, tenant salt derivation, circuit breaker, bot defense

### Data Plane (`src/trueroas/workers/`)
- **Celery Tasks:** `meta_sync`, `shopify_sync`, `reconcile_decisions`, backup/restore
- **DuckDB Tenant Warehouses:** Per-tenant `warehouse.duckdb` files with `historical_metrics`, `decision_audit_trail`, `referrals_outbound`
- **Reconciliation Logic:** 7/30/90-day windows with variable tolerance, Welford's online variance for confidence scoring
- **Security Fixes (2026):**
  - SQL identifier allowlist mapping in `reconcile_decisions.py` prevents injection via column-name interpolation
  - `shutil.which()` resolves `pg_dump`/`sqlite3` paths to prevent PATH hijacking in backup tasks
  - `APP_SECRET_SALT` fail-fast validation on startup; minimum 32 characters enforced

### Learning System (`src/trueroas/learning/`)
- **Pure Python:** `AutoTuner.compute_new_threshold()` uses Brier score with sample-size dampening
- **No WASM dependency:** The Rust/WASM learning core exists in `prod/` but is **not invoked** by the running application
- **Policy Store:** SQLAlchemy-backed `PolicyStore` persists threshold policies with WORM audit trail
- **Deterministic:** Bayesian bias correction is replayable from historical data for audit

### API Routes
| Prefix | Purpose |
|--------|---------|
| `/api/v1/proofs` | ZK proof ingestion with HMAC verification |
| `/api/v1/metrics` | Tenant ROAS metrics + learning metadata |
| `/api/v1/cfo/dashboard` | Business translation + trend charts |
| `/api/v1/admin/leads` | Lead management (admin only) |
| `/api/v1/leads` | Public lead capture |
| `/api/v1/internal/*` | CSV/Excel export endpoints |
| `/api/v1/export/*` | Backwards-compatible audit export aliases |

### Authentication
- JWT Bearer tokens via `HTTPBearer`
- Tenant isolation: every request scoped to `tenant_id` from verified token
- Admin dependencies: `require_admin` for sensitive operations

## Deployment

### Docker Compose (Production)
```bash
docker-compose up -d
```

Services:
- `api` — FastAPI app on port 8001
- `worker` — Celery worker processing meta/shopify/reconciliation tasks
- `db` — PostgreSQL 15 with persistent volume
- `redis` — Redis 7 with password auth

### Environment Variables
```env
POSTGRES_USER=trueroas
POSTGRES_PASSWORD=<required>
POSTGRES_DB=trueroas
REDIS_PASSWORD=<required>
APP_SECRET_SALT=<32+ char secret>
SHOPIFY_TOKEN=<optional, enables LIVE mode>
STRIPE_WEBHOOK_SECRET=<optional>
```

### Local Development
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.trueroas.main:app --reload --port 10000
```

## Security & Compliance

| Control | Implementation |
|---------|---------------|
| **SQL Injection Prevention** | Column names resolved via hardcoded allowlist dicts; no user input reaches SQL identifiers |
| **PATH Hijacking Prevention** | `shutil.which("pg_dump")` / `shutil.which("sqlite3")` resolves binaries before `subprocess.run` |
| **Proof Integrity** | HMAC-SHA256 over canonical JSON; timestamp anti-replay (±300s) |
| **Tenant Isolation** | Per-tenant DuckDB warehouse + PostgreSQL row-level tenant scoping |
| **Secret Management** | `APP_SECRET_SALT` validated at startup; minimum 32 chars; fail-fast on misconfiguration |
| **Bot Defense** | Request fingerprinting + circuit breaker (`AdSpendBreaker`) in `core/breaker.py` |

## Testing

```bash
pytest --cov=src/trueroas
```

- **108 tests** covering API, security, learning, reconciliation, and E2E sandbox
- `test_reconcile_decisions.py`: allowlist completeness, injection char rejection, hardcoded windows validation
- `test_zero_knowledge.py`: ZK compliance (no PII in proof payloads)
- `test_security.py`: tenant sanitization, path traversal, HMAC verification

## Code Quality

```bash
ruff check src/trueroas --select S   # Security linting (0 production errors)
mypy src/trueroas                    # Type checking (104 files, 0 errors)
```

## Legacy Artifacts

The repository contains Rust/WASM source files (`vault.rs`, `self_defense.rs`, `referral.rs`, `lib.rs`, `api.rs`, `models.rs`) and compiled WASM binaries in `prod/` and `deploy/`. These were part of an earlier personalization/tamper-detection architecture that has been **deprecated in favor of the pure-Python FastAPI stack**. The files are retained for reference but are **not loaded or imported** by the running application.

## License

Proprietary. See `ACCOUNTABILITY.md` for compliance and audit details.

© 2026 TrueROAS. All rights reserved.
