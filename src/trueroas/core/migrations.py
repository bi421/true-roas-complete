import duckdb
import os
import logging
import re
import shutil
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from src.trueroas.core.config import settings

# Configure log directory and file path (Project Root/data/logs)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "migrations.log")

# Configure archive directory
ARCHIVE_DIR = os.path.join(LOG_DIR, "archive")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

logger = logging.getLogger("TrueROAS.Migrations")
logger.setLevel(logging.INFO)

# Check for existing handlers to prevent duplicate logging.
if not logger.handlers:
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 1. Console handler.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File handler (TimedRotatingFileHandler).
    # when='D': Rotate daily.
    # interval=1: Every 1 day.
    # backupCount=30: Keep logs for the last 30 days.
    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when='D',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    
    # 1. Set date format with '-'.
    file_handler.suffix = "%Y-%m-%d"
    file_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    # 2. Function to rename log files (migrations.log.YYYY-MM-DD -> YYYY-MM-DD_migrations.log).
    def custom_namer(name):
        dir_path, filename = os.path.split(name)
        if filename.startswith("migrations.log."):
            date_part = filename.split('.')[-1]
            return os.path.join(dir_path, f"{date_part}_migrations.log")
        return name

    file_handler.namer = custom_namer

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Migration list - Applied in sequence.
MIGRATIONS = [
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
    # Version 5: Decision Accountability Tracking.
    """
    CREATE TABLE IF NOT EXISTS decision_audit_trail (
        decision_id VARCHAR PRIMARY KEY,
        account_id VARCHAR,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        recommendation_type VARCHAR,
        predicted_ev DOUBLE,
        predicted_confidence DOUBLE,
        assumptions_json JSON,
        outcome_7d DOUBLE DEFAULT NULL,
        outcome_30d DOUBLE DEFAULT NULL,
        outcome_90d DOUBLE DEFAULT NULL,
        actual_outcome DOUBLE DEFAULT NULL,
        is_successful BOOLEAN DEFAULT NULL,
        reconciled_at TIMESTAMP DEFAULT NULL,
        reconciled_7d_at TIMESTAMP DEFAULT NULL,
        reconciled_30d_at TIMESTAMP DEFAULT NULL,
        reconciled_90d_at TIMESTAMP DEFAULT NULL
    );
    """
]

def cleanup_old_logs():
    """Archive logs and purge archives older than 90 days."""
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
                logger.info(f"Archive: Moved old log file to archive: {file_to_archive}")

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
                    logger.info(f"Purge: Deleted archived log older than 90 days: {archived_file}")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

def apply_migrations(db_path: str):
    """Upgrade tenant database to the latest schema version."""
    tenant_id = os.path.basename(os.path.dirname(db_path))
    with duckdb.connect(db_path) as con:
        # Ensure base directories exist for standard SQLite/DuckDB error prevention on Windows
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Create migration history table.
        con.execute("CREATE TABLE IF NOT EXISTS _migrations (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        
        # Get current version.
        current_version_row = con.execute("SELECT MAX(version) FROM _migrations").fetchone()
        current_version = current_version_row[0] if current_version_row[0] is not None else 0
        
        # Apply pending migrations.
        for i, sql in enumerate(MIGRATIONS):
            version_number = i + 1
            if version_number > current_version:
                try:
                    # 1. Start Transaction: Atomic schema change and version logging.
                    con.execute("BEGIN TRANSACTION")
                    con.execute(sql)
                    con.execute("INSERT INTO _migrations (version) VALUES (?)", [version_number])
                    con.execute("COMMIT")
                    logger.info(f"Migration v{version_number} applied successfully to tenant: {tenant_id}")
                except Exception as e:
                    # 2. Rollback on error: Revert changes made in the current version.
                    con.execute("ROLLBACK")
                    logger.error(f"FATAL: Migration v{version_number} failed for tenant: {tenant_id}. Error: {e}")
                    # Halt migrations if one fails.
                    break

def run_migrations():
    """CLI Entry point to initialize the default tenant database."""
    # This replicates the logic found in main.get_db_path for the default user.
    tenant_dir = os.path.join(BASE_DIR, "data", "tenants", "default")
    os.makedirs(tenant_dir, exist_ok=True)
    db_path = os.path.join(tenant_dir, "warehouse.duckdb")
    apply_migrations(db_path)
    print(f"SUCCESS: Tenant 'default' initialized at {db_path}")