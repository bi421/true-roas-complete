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