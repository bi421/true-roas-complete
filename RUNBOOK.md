# 📖 TrueROAS v2.1 Operational Runbook

## Failure Scenarios & Recovery

### 1. PostgreSQL Connection Pool Exhaustion
**Symptoms:**
*   API requests to `/api/v1/metrics`, `/api/v1/sync` (and others requiring DB access) return `503 Service Unavailable` with `Database Connectivity Failure` in logs.
*   Logs show `sqlalchemy.exc.OperationalError: (psycopg2.errors.TooManyConnections) remaining connection slots are reserved for non-replication superuser connections`.
*   Prometheus `pg_stat_activity_count` metric is near `max_connections`.
**Diagnosis:**
1.  Check `app` container logs: `docker-compose logs -f app | grep "TooManyConnections"`
2.  Check PostgreSQL connection count: `docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"`
3.  Check `db` container logs: `docker-compose logs -f db`
**Mitigation:**
1.  Temporarily restart `app` service to clear stale connections (if any): `docker-compose restart app`
2.  If issue persists, temporarily scale down `app` workers: `docker-compose up -d --scale app=2`
**Resolution:**
1.  Increase `max_connections` in `postgresql.conf` (requires DB restart).
2.  Increase `pool_size` and `max_overflow` in `src/trueroas/core/database.py` (requires `app` restart).
3.  Optimize long-running DB queries (if any) to release connections faster.
**Post-incident:**
*   Review `pg_stat_activity` logs to identify query patterns leading to exhaustion.
*   Implement connection pool metrics in Grafana for proactive alerting.

### 2. Redis Outage
**Symptoms:**
*   API requests return `503 Service Unavailable` with `Redis Connectivity Failure` in logs.
*   Rate limiting fails (requests might pass through or be blocked incorrectly).
*   Celery tasks remain in `PENDING` state, no new tasks are processed.
*   Prometheus `redis_up` metric is `0`.
**Diagnosis:**
1.  Check `app` container logs: `docker-compose logs -f app | grep "Redis Connectivity Failure"`
2.  Check `redis` container status: `docker-compose ps redis`
3.  Verify Redis connectivity from `app` container: `docker-compose exec app redis-cli ping`
**Mitigation:**
1.  Restart Redis container: `docker-compose restart redis`
2.  If Redis is unresponsive, check host system resources (memory, CPU).
**Resolution:**
1.  Investigate root cause of Redis crash (OOM, disk full, network issue).
2.  Implement Redis persistence (RDB/AOF) if not already configured to prevent data loss on restart.
**Post-incident:**
*   Review Redis `maxmemory` settings and eviction policies.
*   Add Redis memory usage and connection count to Grafana dashboard.

### 3. Celery Workers All Down
**Symptoms:**
*   `/api/v1/sync` returns `202 Accepted` but tasks never complete.
*   Celery queue depth (Prometheus `celery_queue_depth`) grows rapidly.
*   `worker` container logs show errors or repeated restarts.
*   `docker-compose ps worker` shows `Exit 1` or `unhealthy`.
**Diagnosis:**
1.  Check `worker` container status: `docker-compose ps worker`
2.  Check `worker` container logs: `docker-compose logs -f worker` (look for exceptions, OOM errors).
3.  Check Celery queue depth: `docker-compose exec redis redis-cli LLEN high` (and medium, low).
**Mitigation:**
1.  Restart `worker` service: `docker-compose restart worker`
2.  If a specific task is causing crashes, revoke it: `docker-compose exec worker celery -A src.trueroas.workers.tasks.celery_app control revoke <task_id>`
**Resolution:**
1.  Analyze `worker` logs for recurring exceptions.
2.  Increase `worker` container resources (CPU, memory) in `docker-compose.yml` if OOM is the cause.
3.  Implement task-level error handling and retry limits to prevent cascading failures.
**Post-incident:**
*   Add alerts for `celery_tasks_completed_total` rate drops and `celery_queue_depth` spikes.
*   Review task code for potential memory leaks or infinite loops.

### 4. Shopify Webhook Signature Verification Fail (Attack or Bug?)
**Symptoms:**
*   `/api/v1/webhooks/shopify` returns `401 Unauthorized`.
*   Logs show `Unauthorized Shopify Webhook attempt from ... Verification failed`.
*   Shopify admin panel shows webhook delivery failures.
**Diagnosis:**
1.  Check `app` container logs: `docker-compose logs -f app | grep "Unauthorized Shopify Webhook"`
2.  Verify `SHOPIFY_API_SECRET` in `.env` matches Shopify admin settings.
3.  Check Shopify webhook logs for recent delivery attempts and payload content.
**Mitigation:**
1.  If suspected attack: Block source IP(s) at firewall/load balancer.
2.  If misconfiguration: Update `SHOPIFY_API_SECRET` in `.env` and restart `app`.
**Resolution:**
1.  If secret mismatch: Update `SHOPIFY_API_SECRET` and ensure it's correctly deployed.
2.  If legitimate Shopify webhook is failing: Investigate network issues or Shopify's side.
3.  If attack: Enhance WAF rules, implement IP rate limiting for webhook endpoint.
**Post-incident:**
*   Implement automated secret rotation for webhooks.
*   Add alerts for `401` responses on webhook endpoints.

### 5. Tenant Database Corruption (WAL Mode Recovery)
**Symptoms:**
*   Specific tenant's API requests (e.g., `/api/v1/metrics`) return `500 Internal Server Error` with `duckdb.Error` or `sqlite3.DatabaseError`.
*   Logs show `database disk image is malformed` or similar.
*   Other tenants are unaffected.
**Diagnosis:**
1.  Check `app` container logs: `docker-compose logs -f app | grep "database disk image is malformed"`
2.  Identify affected tenant `slug` from logs.
3.  Check physical SQLite file: `ls -l ./data/tenants/<tenant_slug>.db*`
**Mitigation:**
1.  Isolate affected tenant (e.g., temporarily disable their access via central DB `Tenant.status`).
2.  WAL mode usually auto-recovers. Try accessing the DB again.
**Resolution:**
1.  If WAL recovery fails: Restore affected tenant's SQLite file from the latest backup.
2.  Investigate root cause of corruption (disk failure, sudden power loss, application bug writing bad data).
**Post-incident:**
*   Implement regular integrity checks (`PRAGMA integrity_check;`) on tenant DBs.
*   Enhance tenant DB backup strategy (e.g., hourly snapshots).

### 6. Stripe Webhook Duplicate Event (Idempotency Fail)
**Symptoms:**
*   Stripe dashboard shows multiple `checkout.session.completed` events for the same session.
*   Logs show `Stripe attempt from ...: Duplicate event <event_id>`.
*   Tenant might be double-charged or have multiple active subscriptions.
**Diagnosis:**
1.  Check `app` container logs: `docker-compose logs -f app | grep "Duplicate event"`
2.  Check Redis for idempotency key: `docker-compose exec redis redis-cli GET webhook:id:<event_id>`
3.  Review Stripe event logs for re-delivery attempts.
**Mitigation:**
1.  Manually correct tenant's subscription status in central PostgreSQL.
2.  If Redis is unstable, restart it.
**Resolution:**
1.  Investigate why Redis idempotency key was not set or expired prematurely.
2.  Review webhook processing logic for race conditions.
**Post-incident:**
*   Add alerts for `Duplicate event` logs.
*   Implement a reconciliation job to detect and correct duplicate subscriptions.

### 7. Bayesian Posterior Calculation Returns NaN
**Symptoms:**
*   `/api/v1/metrics` or `/api/v1/sync` tasks return `500 Internal Server Error` with `ValueError: Non-finite values` in logs.
*   Logs show `Non-finite mean calculated` or `Non-finite variance calculated`.
*   Prometheus `bayesian_reconciliation_duration_seconds` might show high latency or errors.
**Diagnosis:**
1.  Check `app` or `worker` logs: `docker-compose logs -f app | grep "Non-finite"`
2.  Identify input parameters (`meta_roas`, `true_roas`, `std_dev`, `sample_size`) that led to the `NaN`.
**Mitigation:**
1.  If a specific tenant's data is causing it, temporarily disable their Bayesian calculations.
**Resolution:**
1.  Review `src/trueroas/core/inference.py` for edge cases not covered by `math.isfinite()` checks.
2.  Enhance input validation to reject extreme values (e.g., `std_dev` near `0` with `sample_size=1`).
3.  Add more property-based tests (Hypothesis) for `DecisionEngine` methods with extreme inputs.
**Post-incident:**
*   Implement data quality checks on incoming `meta_roas`, `true_roas` to prevent `NaN` propagation.

### 8. Meta API Rate Limit (503 from Meta)
**Symptoms:**
*   `sync_meta_data` Celery tasks fail with `httpx.HTTPStatusError: 503 Service Unavailable` or `400 Bad Request` from Meta API.
*   Logs show `Meta API: Failed to pause campaign ...` or `Meta API rate limit exceeded`.
*   Data synchronization is delayed or incomplete.
**Diagnosis:**
1.  Check `worker` container logs: `docker-compose logs -f worker | grep "Meta API"`
2.  Review Meta for Developers dashboard for API usage and rate limit status.
**Mitigation:**
1.  Implement exponential backoff and retry logic for Meta API calls (already in Celery task).
2.  Temporarily reduce the frequency or concurrency of `sync_meta_data` tasks.
**Resolution:**
1.  If persistent: Request higher rate limits from Meta.
2.  Optimize Meta API calls to fetch data in batches, reducing individual call count.
3.  Implement a dedicated Meta API client with built-in rate limiting and token management.
**Post-incident:**
*   Add Prometheus metrics for Meta API call success/failure rates and latency.
*   Alert on `5xx` responses from Meta API.

### 9. Disk Full (`/data/tenants/` дүүрсэн)
**Symptoms:**
*   New tenant creation fails.
*   SQLite tenant DB writes fail.
*   Logs show `No space left on device`.
*   `df -h` on host shows `/data` volume is full.
**Diagnosis:**
1.  Check `app` or `worker` logs: `docker-compose logs -f app | grep "No space"`
2.  Check host disk usage: `df -h`
3.  Check `data` volume usage: `du -sh ./data`
**Mitigation:**
1.  Temporarily pause new tenant creation.
2.  Identify and delete non-critical large files (e.g., old backups, temporary files).
**Resolution:**
1.  Increase disk size of the host machine or Docker volume.
2.  Implement aggressive data retention policies for audit logs and historical metrics.
3.  Implement external archival to S3/cold storage for old tenant data.
**Post-incident:**
*   Add Prometheus alerts for disk usage exceeding 80% on `/data` volume.
*   Review `monitor_db_sizes` task for effectiveness.

### 10. APP_SECRET_SALT Leak Suspected
**Symptoms:**
*   Unauthorized access to tenant data (e.g., `grep` for PII in `/data/tenants/` returns plaintext).
*   Unexpected changes in tenant data (e.g., `decision_audit_trail` checksum mismatch).
*   External security scan reports `APP_SECRET_SALT` in public repository or logs.
**Diagnosis:**
1.  Immediately check `APP_SECRET_SALT` in `.env` and ensure it's not committed to version control.
2.  Review `docker-compose.yml` and `Dockerfile` for accidental exposure.
3.  Check `app` and `worker` logs for `APP_SECRET_SALT` in plaintext.
**Mitigation:**
1.  **IMMEDIATELY ROTATE `APP_SECRET_SALT`**: Generate a new, strong secret and update `.env` on all production instances.
2.  Restart all `app` and `worker` containers.
3.  Invalidate all existing JWT tokens (if possible, by restarting `app` or implementing JWT blacklisting).
**Resolution:**
1.  Perform a full security audit of the codebase and infrastructure.
2.  Implement a secret management solution (e.g., HashiCorp Vault, AWS Secrets Manager) to prevent direct exposure of `APP_SECRET_SALT`.
3.  Re-hash all existing PII data in tenant SQLite databases using the new `APP_SECRET_SALT` (complex, requires downtime).
**Post-incident:**
*   Conduct mandatory security training for all developers on secret management best practices.
*   Implement automated secret scanning in CI/CD pipeline.

### 11. PostgreSQL Primary Failure / Data Corruption
**Symptoms:**
*   Grafana: `PostgreSQL connections = 0`, `query rate = 0`.
*   App logs: `"could not connect to server: Connection refused"` or `"checksum failure"`.
*   PagerDuty: `"PostgreSQL primary down"` or `"data corruption detected"`.
*   Tenant sync jobs failing with database errors.
**Diagnosis:**
```bash
# Check connectivity from within the cluster
pg_isready -h $DB_HOST -p 5432
# Check for hardware/filesystem errors in DB logs
docker-compose logs db | grep -E "PANIC|FATAL|corruption"
# Check if replica is healthy and lag
psql -h $PG_REPLICA_HOST -c "SELECT pg_is_in_recovery(), pg_last_xact_replay_timestamp(), now()-pg_last_xact_replay_timestamp() AS lag;"
```
**Mitigation:**
1.  Identify if failure is regional or instance-specific.
2.  If Primary is down but Replica is healthy and lag is < 5s: Initiate failover to Replica.
3.  Enable "Maintenance Mode" (Read-Only) in application settings to prevent further corruption.
**Resolution:**
1.  Promote Replica to Primary.
2.  Update `POSTGRES_URL` in environment variables/Secrets Manager.
3.  If both are corrupted: Restore from latest nightly BRT verified backup using `brt_audit.py`.
**Post-incident:**
*   Analyze `pg_stat_replication` history for lag trends.
*   Verify `PRAGMA integrity_check` on all restored tenant SQLite warehouses.
*   Review RPO/RTO targets based on actual recovery time.

---
*Proprietary and Confidential | TrueROAS Ops Team*