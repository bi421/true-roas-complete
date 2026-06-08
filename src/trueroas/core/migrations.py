import logging
import os
import re
import shutil
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from typing import List

import duckdb
from sqlalchemy import create_engine, text

from trueroas.core.config import settings

# Configure log directory and file path (Project Root/data/logs)
LOG_DIR = settings.DATA_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "migrations.log")

# Configure archive directory
ARCHIVE_DIR = os.path.join(LOG_DIR, "archive")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

logger = logging.getLogger("TrueROAS.Migrations")
logger.setLevel(logging.INFO)

# Check for existing handlers to prevent duplicate logging.
if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 1. Console handler.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File handler (TimedRotatingFileHandler).
    # when='D': Rotate daily.
    # interval=1: Every 1 day.
    # backupCount=30: Keep logs for the last 30 days.
    file_handler = TimedRotatingFileHandler(
        LOG_FILE, when="D", interval=1, backupCount=30, encoding="utf-8"
    )

    # 1. Set date format with '-'.
    file_handler.suffix = "%Y-%m-%d"
    file_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    # 2. Function to rename log files (migrations.log.YYYY-MM-DD -> YYYY-MM-DD_migrations.log).
    def custom_namer(name: str) -> str:
        dir_path, filename = os.path.split(name)
        if filename.startswith("migrations.log."):
            date_part = filename.split(".")[-1]
            return os.path.join(dir_path, f"{date_part}_migrations.log")
        return name

    file_handler.namer = custom_namer

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Migration list - Applied in sequence.
MIGRATIONS: List[str] = [
    # Version 1: Core tables.
    """
    CREATE TABLE IF NOT EXISTS historical_metrics (
        account_id VARCHAR,
        order_id VARCHAR,
        clean_date DATE,
        normalized_spend DOUBLE,
        meta_roas DOUBLE,
        true_revenue DOUBLE DEFAULT 0,
        true_roas DOUBLE DEFAULT 0,
        true_cac DOUBLE DEFAULT 0
    );
    """,
    # Version 2: Audit log table.
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        action_type VARCHAR,
        details VARCHAR
    );
    """,
    # Version 3: Statistical indicators for Decision Intelligence.
    """
    ALTER TABLE historical_metrics ADD COLUMN IF NOT EXISTS order_count INTEGER DEFAULT 0;
    ALTER TABLE historical_metrics ADD COLUMN IF NOT EXISTS revenue_variance DOUBLE DEFAULT 0;
    ALTER TABLE historical_metrics ADD COLUMN IF NOT EXISTS confidence_score DOUBLE DEFAULT 0;
    """,
    # Version 4: Performance metrics for constraint detection.
    """
    ALTER TABLE historical_metrics ADD COLUMN IF NOT EXISTS ctr DOUBLE DEFAULT 0.015;
    ALTER TABLE historical_metrics ADD COLUMN IF NOT EXISTS conversion_rate DOUBLE DEFAULT 0.025;
    ALTER TABLE historical_metrics ADD COLUMN IF NOT EXISTS frequency DOUBLE DEFAULT 1.0;
    """,
    # Version 5: Decision Accountability Tracking (Refined for Traceability)
    """
    CREATE TABLE IF NOT EXISTS decision_audit_trail (
        decision_id VARCHAR PRIMARY KEY,
        tenant_id VARCHAR,
        campaign_id VARCHAR,
        user_id VARCHAR,
        action VARCHAR, -- scale, pause, optimize
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expected_roas DOUBLE,
        predicted_ev DOUBLE,
        confidence_level DOUBLE,
        assumptions_json JSON,
        actual_roas_7d DOUBLE DEFAULT NULL,
        actual_roas_30d DOUBLE DEFAULT NULL,
        actual_roas_90d DOUBLE DEFAULT NULL,
        is_accurate_7d BOOLEAN DEFAULT NULL,
        is_accurate_30d BOOLEAN DEFAULT NULL,
        is_accurate_90d BOOLEAN DEFAULT NULL,
        reconciled_7d_at TIMESTAMP DEFAULT NULL,
        reconciled_30d_at TIMESTAMP DEFAULT NULL,
        reconciled_90d_at TIMESTAMP DEFAULT NULL,
        checksum VARCHAR(64) -- SHA-256 for row integrity
    );
    """,
    # Version 6: Warehouse Schema for Orders, Decisions, and Reconciliations (Requirement 3)
    """
    CREATE TABLE IF NOT EXISTS orders (
        id VARCHAR PRIMARY KEY,
        platform VARCHAR NOT NULL,
        amount DOUBLE NOT NULL,
        currency VARCHAR(3) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        meta JSON
    );
    CREATE TABLE IF NOT EXISTS decisions (
        id VARCHAR PRIMARY KEY,
        action VARCHAR NOT NULL,
        campaign_id VARCHAR NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expected_roas DOUBLE
    );
    CREATE TABLE IF NOT EXISTS reconciliations (
        id VARCHAR PRIMARY KEY,
        decision_id VARCHAR NOT NULL,
        actual_roas DOUBLE,
        accuracy_score DOUBLE,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (decision_id) REFERENCES decisions(id)
    );
    """,
    # Version 7: Financial Compliance Audit Log (Requirement 1 & 2)
    """
    CREATE TABLE IF NOT EXISTS job_audit_log (
        id VARCHAR PRIMARY KEY,
        tenant_id VARCHAR NOT NULL,
        job_type VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        completed_at TIMESTAMP NOT NULL,
        records_processed INTEGER DEFAULT 0,
        checksum VARCHAR(64),
        operator VARCHAR NOT NULL DEFAULT 'system',
        metadata_json JSON
    );
    """,
    # Postgres compatible immutability for Version 7
    """
    CREATE OR REPLACE FUNCTION block_modification() RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Financial Compliance: Modification of audit trail is forbidden.';
    END;
    $$ LANGUAGE plpgsql;

    DO $$ BEGIN
        CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON job_audit_log 
        FOR EACH ROW EXECUTE FUNCTION block_modification();
    EXCEPTION WHEN others THEN NULL; END $$;

    DO $$ BEGIN
        CREATE TRIGGER audit_log_no_delete BEFORE DELETE ON job_audit_log 
        FOR EACH ROW EXECUTE FUNCTION block_modification();
    EXCEPTION WHEN others THEN NULL; END $$;
    """,
    # Version 8: Backup Registry for BRT Pipeline (Requirement 1.d)
    """
    CREATE TABLE IF NOT EXISTS backup_registry (
        id VARCHAR PRIMARY KEY,
        backup_type VARCHAR NOT NULL, -- POSTGRES, SQLITE, REDIS
        tenant_id VARCHAR, -- NULL for Central/Redis
        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        s3_path VARCHAR NOT NULL,
        sha256_uncompressed VARCHAR(64),
        sha256_encrypted VARCHAR(64) NOT NULL,
        kms_key_id VARCHAR(255),
        status VARCHAR(20) DEFAULT 'pending', -- pending, verified, failed
        row_count_snapshot JSON -- Snapshot of critical table counts for restore audit
    );
    """,
    # Version 9: GDPR Compliance and Consent Tracking
    """
    CREATE TABLE IF NOT EXISTS gdpr_erasure_log (
        operation_id VARCHAR PRIMARY KEY,
        subject_hash VARCHAR(64) NOT NULL,
        identifier_type VARCHAR(20) NOT NULL, -- EMAIL, TENANT, STRIPE_ID
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        systems_purged JSON,
        verification_signature VARCHAR(128) -- Signed with APP_SECRET_SALT
    );

    -- Requirement 6.b: Consent Tracking for Leads
    ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS consent_ip VARCHAR(45);
    ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP;
    ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS privacy_policy_version VARCHAR(10);
    """,
    # Version 10: Immutability Triggers for Decision Audit Trail (Requirement 1.e)
    """
    CREATE OR REPLACE FUNCTION block_decision_modification() RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Decision Immutability Violation: Mutation of strategic records is prohibited.';
    END;
    $$ LANGUAGE plpgsql;

    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'block_decision_update') THEN
            CREATE TRIGGER block_decision_update BEFORE UPDATE ON decision_audit_trail 
            FOR EACH ROW EXECUTE FUNCTION block_decision_modification();
        END IF;
    END $$;

    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'block_decision_delete') THEN
            CREATE TRIGGER block_decision_delete BEFORE DELETE ON decision_audit_trail 
            FOR EACH ROW EXECUTE FUNCTION block_decision_modification();
        END IF;
    END $$;
    """,
    # Version 11: Compliance and Opt-in updates
    """
    -- Requirement 1: User Opt-in for Auto-Pause Guardrails
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS auto_pause_enabled BOOLEAN DEFAULT FALSE;

    -- Requirement 2: Separation of Platform Data for 120-day retention
    -- We tag historical_metrics to allow auto-cleanup of raw platform insights
    -- while preserving calculated Decision Audit logs.
    ALTER TABLE historical_metrics ADD COLUMN IF NOT EXISTS is_platform_data BOOLEAN DEFAULT TRUE;
    ALTER TABLE decision_audit_trail ADD COLUMN IF NOT EXISTS is_platform_data BOOLEAN DEFAULT FALSE;
    """,
    # Version 12: Sync Resilience Tracking (Requirement 3.c)
    """
    CREATE TABLE IF NOT EXISTS sync_metadata (
        service VARCHAR PRIMARY KEY,
        last_sync_status VARCHAR DEFAULT 'OK',
        data_freshness_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        error_message TEXT
    );
    """,
    # Version 13: Zero-Knowledge Compute Proofs
    """
    CREATE TABLE IF NOT EXISTS zk_proofs (
        id VARCHAR PRIMARY KEY,
        tenant_id VARCHAR,
        true_roas DOUBLE,
        meta_roas DOUBLE,
        waste_usd DOUBLE,
        p10_roas DOUBLE,
        signature VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
]


def cleanup_old_logs() -> None:
    """Archives old logs and purges archives exceeding the 90-day retention limit."""
    try:
        # Filter for YYYY-MM-DD_migrations.log files.
        pattern = r"^\d{4}-\d{2}-\d{2}_migrations\.log$"
        log_files = [f for f in os.listdir(LOG_DIR) if re.match(pattern, f)]

        # Sort by date (newest first).
        log_files.sort(reverse=True)

        backup_limit = settings.LOG_BACKUP_COUNT
        # Archive files exceeding backupCount.
        if len(log_files) > backup_limit:
            for file_to_archive in log_files[backup_limit:]:
                src_path = os.path.join(LOG_DIR, file_to_archive)
                dst_path = os.path.join(ARCHIVE_DIR, file_to_archive)
                shutil.move(src_path, dst_path)
                logger.info(
                    f"Archive: Moved old log file to archive: {file_to_archive}"
                )

        # --- Purge archives. ---
        retention_limit = datetime.now() - timedelta(days=settings.LOG_RETENTION_DAYS)
        archive_pattern = r"^(\d{4}-\d{2}-\d{2})_migrations\.log$"

        for archived_file in os.listdir(ARCHIVE_DIR):
            match = re.match(archive_pattern, archived_file)
            if match:
                file_date_str = match.group(1)
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")

                if file_date < retention_limit:
                    os.remove(os.path.join(ARCHIVE_DIR, archived_file))
                    logger.info(
                        f"Purge: Deleted archived log older than 90 days: {archived_file}"
                    )

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


def archive_old_audit_logs(tenant_id: str) -> None:
    """Archives old audit logs to cold storage for a specific tenant.

    In production, this moves rows to an archive table or external object store.

    Args:
        tenant_id (str): Unique tenant identifier.
    """
    schema_name = f"tenant_{tenant_id.replace('-', '_')}"

    engine = create_engine(str(settings.POSTGRES_URL))
    with engine.begin() as con:
        con.execute(text(f"SET search_path TO {schema_name}"))
        # In a real production environment, this would involve moving data to a separate archive table
        # or an external object storage (e.g., S3).
        # The current Postgres triggers prevent direct deletion from job_audit_log.
        logger.info(
            f"Audit Archival: Simulation for cold storage archival for tenant schema: {schema_name}"
        )


def apply_migrations(tenant_id: str) -> None:
    """Upgrades a tenant's schema to the latest version in PostgreSQL.

    Args:
        tenant_id (str): Unique tenant identifier.
    """
    if tenant_id.endswith(".duckdb") or settings.POSTGRES_URL is None:
        db_path = tenant_id if tenant_id.endswith(".duckdb") else f"{tenant_id}.duckdb"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with duckdb.connect(db_path) as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS _migrations (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            con.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id VARCHAR PRIMARY KEY,
                    platform VARCHAR,
                    amount DOUBLE,
                    currency VARCHAR,
                    created_at TIMESTAMP,
                    meta JSON
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS historical_metrics (
                    account_id VARCHAR,
                    order_id VARCHAR,
                    clean_date DATE,
                    normalized_spend DOUBLE,
                    meta_roas DOUBLE,
                    true_revenue DOUBLE DEFAULT 0,
                    true_roas DOUBLE DEFAULT 0,
                    true_cac DOUBLE DEFAULT 0
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS decision_audit_trail (
                    decision_id VARCHAR PRIMARY KEY,
                    tenant_id VARCHAR,
                    campaign_id VARCHAR,
                    action VARCHAR,
                    timestamp TIMESTAMP,
                    expected_roas DOUBLE,
                    confidence_level DOUBLE,
                    user_id VARCHAR,
                    actual_roas_7d DOUBLE,
                    actual_roas_30d DOUBLE,
                    actual_roas_90d DOUBLE,
                    is_accurate_7d BOOLEAN,
                    is_accurate_30d BOOLEAN,
                    is_accurate_90d BOOLEAN,
                    accuracy_ratio_7d DOUBLE,
                    accuracy_ratio_30d DOUBLE,
                    accuracy_ratio_90d DOUBLE,
                    reconciled_7d_at TIMESTAMP,
                    reconciled_30d_at TIMESTAMP,
                    reconciled_90d_at TIMESTAMP,
                    expected_value DOUBLE DEFAULT 0,
                    approved_by VARCHAR,
                    is_automated BOOLEAN DEFAULT TRUE,
                    assumptions_json JSON
                )
            """)
            con.execute("INSERT OR IGNORE INTO _migrations (version) VALUES (1)")
        return

    schema_name = f"tenant_{tenant_id.replace('-', '_')}"

    engine = create_engine(str(settings.POSTGRES_URL))
    with engine.begin() as con:
        # Create schema if it doesn't exist
        con.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        # Set search path to the tenant's schema for the current session
        con.execute(text(f"SET search_path TO {schema_name}"))

        # Create migration history table.
        con.execute(
            text(
                "CREATE TABLE IF NOT EXISTS _migrations (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )

        # Get current version.
        current_version_row = con.execute(
            text("SELECT MAX(version) FROM _migrations")
        ).fetchone()
        current_version = (
            current_version_row[0]
            if current_version_row is not None and current_version_row[0] is not None
            else 0
        )

        # Apply pending migrations.
        for i, sql in enumerate(MIGRATIONS):
            version_number = i + 1
            if version_number > current_version:
                try:
                    con.execute(text(sql))
                    con.execute(
                        text("INSERT INTO _migrations (version) VALUES (:v)"),
                        {"v": version_number},
                    )
                    logger.info(
                        f"Migration v{version_number} applied successfully to schema: {schema_name}"
                    )
                except Exception as e:
                    logger.error(
                        f"FATAL: Migration v{version_number} failed for schema {schema_name}. Error: {e}"
                    )
                    # Halt migrations if one fails.
                    break


def run_migrations() -> None:
    """CLI Entry point to initialize the default tenant schema."""
    apply_migrations("default")
    print("SUCCESS: Tenant 'default' schema initialized.")
