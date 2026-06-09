#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import logging
from sqlalchemy import text
from trueroas.core.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trueroas.learning.migrate")


def migrate_learning_table() -> None:
    """Additive migration: Creates learning_policies table."""
    db = SessionLocal()
    try:
        logger.info("Applying additive migration for learning system...")
        db.execute(
            text("""
            CREATE TABLE IF NOT EXISTS learning_policies (
                id SERIAL PRIMARY KEY,
                tenant_id VARCHAR(64) NOT NULL,
                config_json TEXT NOT NULL,
                signature VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        )
        db.commit()
        logger.info("Migration successful.")
    finally:
        db.close()
