# 🚀 TrueROAS v2.1 | Production Deployment Checklist

This checklist verifies that all strategic, technical, and compliance guardrails are active before transitioning the platform to live scaling data.

## 🛡️ Validation Prompts & Audits
- [ ] **Security (1.1-1.3):** All prompts passed. 
  - HMAC-SHA256 salt derivation verified for multi-tenancy.
  - PII hashing (BLAKE2b) active for email/phone.
  - Shannon Entropy checks (>3.5 bits) enforced on master secrets.
- [ ] **Database (2.1-2.2):** Migration integrity verified.
  - PostgreSQL metadata layer pooling configured (max_overflow=10).
  - Per-tenant SQLite warehouses active with WAL mode and 0600 permissions.
  - Migration history table (`_migrations`) verified on default tenant.
- [ ] **Analytics (3.1-3.3):** Statistical unit tests green.
  - Normal-Normal conjugate prior formulas verified in `inference.py`.
  - 95% Credible Intervals and Risk-Adjusted ROAS exposed via API.
  - Posterior caching in Redis (1h TTL) verified.
- [ ] **API (4.1-4.3):** Integration tests passed.
  - Coverage for 200 (Success), 400 (Validation), 401 (Unauthorized), 429 (Rate Limit), and 500 (Global Error) codes.
  - JWT multi-tenant authorization verified for sync and metrics endpoints.
- [ ] **Infrastructure (5.1-5.3):** Docker health checks reporting healthy.
  - Multi-stage `Dockerfile` verified (non-root UID 1000).
  - Resource limits enforced for app (512MB) and worker (1GB).
  - Celery priority queues (High/Medium/Low) routing verified.
- [ ] **Compliance (6.1-6.2):** Legal review sign-off.
  - GDPR Export/Delete endpoints active with 30-day purge cycle.
  - Financial audit trail hardened (Append-only job logs with digital signatures).
  - Cookie consent and DPA links verified on landing page.
- [ ] **E2E (7.1-7.2):** Load and Chaos tests attached.
  - [ ] **Load Test:** Staging stress test pending (Validated locally with `test_performance.py`).
  - [ ] **Crash Recovery:** Worker crash recovery (kill -9) verified in sandbox.

## 🚨 Critical Blockers (Must be resolved before Production)
- [x] **Infrastructure Provisioning:** Verified via `terraform plan`. Ready for final `apply`.
- [ ] **Restore Validation:** Automated monthly test of database backup restoration process.
- [x] **Math & Edge-Case Safety:** `inference.py` engine fuzzed with Hypothesis in `tests/property/test_production_fuzzing.py`.
- [ ] **Final Preflight:** `production_preflight.ps1` executed and all gates green.
## 🌐 Network & Access
- [ ] **Domain Setup:** DNS configuration and official SSL/TLS certificates pending.
## ⚙️ Operational Readiness
- [ ] **SSL/TLS Certificates:** Configured via Cloudflare or Nginx with HSTS enabled and minimum TLS 1.2.
- [ ] **Secrets Rotation:** Production keys for Stripe, Resend, and Meta rotated. Old development keys invalidated.
- [ ] **Incident Response:** Runbook (`RUNBOOK.md`) published and accessible to the on-call team.
- [ ] **Backup Verification:** Nightly `pg_dump` scheduled; test restore performed on a fresh instance.
- [ ] **Rollback Plan:** `docker-compose.yml` image versioning tested on staging to ensure < 30s rollback.

## 📈 Monitoring Dashboard
- [ ] Prometheus `/metrics` endpoint reachable by Prometheus server.
- [ ] Grafana alerts configured for 5xx rates > 1% and Celery backlog > 1000.
- [ ] Structured JSON logs flowing to centralized log management (ELK/Datadog/CloudWatch).

---
*© 2024-2026 TrueROAS Team. All rights reserved.*
*Accountability before Scale.*