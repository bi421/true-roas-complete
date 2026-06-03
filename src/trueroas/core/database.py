import hashlib
import hmac
import sqlite3
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator

from src.trueroas.core.config import settings

class BaseDatabase(ABC):
    @abstractmethod
    def get_connection(self, tenant_id: str): pass

# SQLAlchemy Declarative Base for central metadata
Base = declarative_base()

# Central Database for Subscriptions and Global Metadata
# Uses SQLite for local-first metadata, or PostgreSQL if configured
CENTRAL_DB_URL = str(settings.POSTGRES_URL) if settings.DATABASE_TYPE == "postgres" else f"sqlite:///{settings.DATA_DIR}/central.db"

engine_args = {"connect_args": {"check_same_thread": False}} if "sqlite" in CENTRAL_DB_URL else {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_recycle": 3600,
    "pool_pre_ping": True  # Verification of connection health before use
}

engine = create_engine(CENTRAL_DB_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session() -> Generator[Session, None, None]:
    """Dependency for providing a database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SQLiteTenantDatabase(BaseDatabase):
    def __init__(self):
        self._local = threading.local()

    def get_warehouse_path(self, tenant_id: str) -> Path:
        from src.trueroas.services.security import sanitize_tenant_id
        safe_id = sanitize_tenant_id(tenant_id)
        # Requirement 1: Each tenant gets a dedicated .db file named {tenant_id}.db in /data/tenants/
        path = (settings.DATA_DIR / "tenants" / f"{safe_id}.db").resolve()
        return path

    def get_connection(self, tenant_id: str):
        if not hasattr(self._local, 'conns'): self._local.conns = {}
        if tenant_id not in self._local.conns:
            db_path = self.get_warehouse_path(tenant_id)
            # Ensure directory exists and file has restrictive permissions
            db_path.parent.mkdir(parents=True, exist_ok=True)
            if not db_path.exists():
                db_path.touch(mode=0o600)
            
            # Requirement 4: High timeout parameter prevents "database is locked" errors during 50+ concurrent syncs
            conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            # Requirement 2: Ensure automatic WAL checkpointing happens at 1000 pages
            conn.execute("PRAGMA wal_autocheckpoint=1000;")
            conn.row_factory = sqlite3.Row
            self._local.conns[tenant_id] = conn
        return self._local.conns[tenant_id]

db_layer = SQLiteTenantDatabase()

def hash_identifier(tenant_id: str, raw_value: str, tenant_secret_salt: str) -> str:
    """
    Hashes PII using Keyed BLAKE2b with a combined key:
    HMAC-SHA256(APP_SECRET_SALT, tenant_secret_salt_from_pg)
    """
    if not raw_value: return ""
    pepper = settings.APP_SECRET_SALT.encode()
    # Derive per-tenant key using the pepper and the UUID salt from metadata
    derived_key = hmac.new(pepper, tenant_secret_salt.encode(), hashlib.sha256).digest()
    return hashlib.blake2b(raw_value.encode(), key=derived_key, digest_size=32).hexdigest()

def get_db_path(tenant_id: str = "default") -> str:
    return str(db_layer.get_warehouse_path(tenant_id))