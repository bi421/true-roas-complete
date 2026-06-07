# Changelog

## [1.3.0] - 2026-06-04 - Production Integrity Release
### Infrastructure
- **API Hardening:** Converted all mock endpoints in `main.py` to production task-runners.
- **CFO Dashboard:** Finalized Bayesian P10 calculation using dynamic standard deviation via SciPy.
- **CAPI Resilience:** Implemented `event_id` deduplication in CSV exports to prevent Meta double-counting.
- **Observability:** Integrated structured JSON logging across the Celery worker pool for SOC2 traceability.

## [1.2.0] - 2026-06-03 - Strategic Pivot: Decision Accountability
### Positioning
- **Category Creation:** Re-positioned TrueROAS from a "Marketing Audit" tool to a **"Decision Accountability Platform"**.
- **Messaging Overhaul:** Shifted from fear-based marketing ("Leakage") to value-based accountability ("Decision Verification").
- **Comparison Logic:** Integrated "Analytics vs. Accountability" frameworks into documentation and landing page.
- **Trust Cleanup:** Removed non-certified compliance claims and placeholder social proof to ensure professional integrity.

## [1.1.0] - 2026-06-03 - Production Hardening
### Architecture
- **Database Migration:** Replaced DuckDB with a multi-tenant SQLite architecture (WAL mode) and PostgreSQL support for high-concurrency environments.
- **Task Orchestration:** Integrated Celery + Redis for non-blocking data synchronization and report generation.
- **Event-Driven Reconciliation:** Added Shopify Webhook handlers (`orders/create`, `refunds/create`) to trigger incremental syncs.
- **Async Reporting:** Implemented a background PDF service using WeasyPrint with Jinja2 template caching.

### Security
- **PII Isolation:** Implemented per-tenant salt derivation using `HMAC-SHA256` and `BLAKE2b` hashing.
- **Filesystem Protection:** Added strict path sanitization and resolution validation to prevent directory traversal.
- **Audit Tracing:** Added Request ID middleware and structured logging for transaction traceability.

### Statistics
- **Empirical Bayes:** Replaced static priors with historical variance estimation.
- **Bootstrap Fallback:** Added non-parametric bootstrap posterior estimation for datasets with `n < 30` (replaces Normal approximation).
- **Diagnostics:** Added skewness and kurtosis checks to posterior distributions to flag Normal model misspecification.

### Decision Intelligence
- **Multi-Constraint Scoring:** Replaced the legacy `elif` bottleneck chain with a scored multi-constraint detection model.
- **Vertical Calibration:** Added support for industry-specific benchmarks (Beauty, Apparel, etc.) for more accurate funnel diagnostics.
- **Empirical Lever Simulation:** Replaced arbitrary 15% improvement assumptions with historical "Best Achievable" peak performance analysis.
- **Threshold Hardening:** Migrated all "magic numbers" to validated Pydantic settings.

### API
- **Modular Routing:** Restructured `main.py` into specialized route modules (`sync`, `analysis`, `reports`, `webhooks`).
- **Resilience:** Implemented global structured exception handling and Pydantic-v2 request validation.
- **Task Polling:** Added `/api/v1/tasks/{task_id}` for real-time status tracking of background operations.

### Testing
- **Test Coverage:** Implemented a 3-layer suite: Unit, Integration, and Property-based (Hypothesis).
- **Math Verification:** Added regression tests for Bayesian posterior means and Welford's algorithm consistency.
- **Security Auditing:** Added automated tests for path traversal injection and hashing collisions.

### UX/UI
- **Lead Capture:** Replaced inefficient `mailto:` links with a high-conversion email capture form in the Hero section.
- **Social Proof:** Integrated customer testimonials and "Trusted By" sections to build market credibility.
- **Pricing Transparency:** Introduced a 2-tier pricing model ($79/$199) to qualify leads and anchor value.
- **Interactive Exports:** Implemented a Modal-driven interface for CSV exports with custom date range selection (7-90 days).
- **Result Sharing:** Integrated Web Share API for native mobile sharing of audit findings.

### Utilities & Legal
- **Copyright Automation:** Implemented a Python utility script to enforce standardized proprietary headers across all source files.
- **Legal Compliance:** Standardized copyright notices (© 2024-2026) across the landing page, README, and source code.

### DevOps
- **Orchestration:** Added a production-ready `docker-compose.yml` defining API, Worker, Beat, and Redis services.
- **Environment Parity:** Provided `.env.example` documenting all mathematical and strategic thresholds.