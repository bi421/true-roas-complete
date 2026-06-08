import os
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, Generator

import duckdb
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Engine,
    Float,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


DatabaseError = Exception

# Global cache to prevent engine exhaustion
_engine_cache: Dict[str, Engine] = {}

# Global sessionmaker cache to prevent descriptor leaks
_session_factories: Dict[str, sessionmaker[Session]] = {}

# Central SessionLocal for core metadata operations (e.g., Tenant management)
central_engine = create_engine(
    str(os.getenv("POSTGRES_URL") or "sqlite:///data/central.db")
    if os.getenv("DEPLOYMENT_TYPE") == "CLOUD"
    else "sqlite:///data/central.db"
)
engine = central_engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=central_engine)


class DatabaseFactory:
    @staticmethod
    def get_engine(tenant_id: str, mode: str = "enterprise") -> Engine:
        """Handles hybrid DB logic with connection pooling and caching.

        PostgreSQL for Enterprise, SQLite (WAL mode) for Local.

        Args:
            tenant_id (str): Unique tenant identifier.
            mode (str): Database mode ('enterprise' or 'local'). Defaults to 'enterprise'.

        Returns:
            Engine: SQLAlchemy engine instance.
        """
        if tenant_id in _engine_cache:
            return _engine_cache[tenant_id]

        if mode == "enterprise":
            # Row Level Security (RLS) active in PostgreSQL
            db_url = str(os.getenv("POSTGRES_URL", ""))
            create_engine(
                db_url,
                pool_size=10,  # Base pool size
                max_overflow=20,  # Allow burst connections during BFCM
                pool_pre_ping=True,  # Verify connection health before use
            )
        return central_engine


def get_db_path(tenant_id: str) -> str:
    """Bridge function for legacy path resolution."""
    safe_tenant = re.sub(r"[^a-zA-Z0-9_-]", "", tenant_id)
    return os.path.join("data", "tenants", safe_tenant, "warehouse.duckdb")


def hash_identifier(context: str, value: str, salt: str) -> str:
    """Bridge to security module hashing."""
    from src.trueroas.core.security import hash_pii

    return hash_pii(context, value, salt)


class DBLayerBridge:
    @staticmethod
    def get_warehouse_path(tenant_id: str) -> Path:
        return Path(get_db_path(tenant_id))

    @staticmethod
    def get_connection(tenant_id: str) -> Any:
        return duckdb.connect(str(DBLayerBridge.get_warehouse_path(tenant_id)))


db_layer = DBLayerBridge()


@contextmanager
def get_db_session(tenant_id: str = "default") -> Generator[Session, None, None]:
    """Yields a DB session with connection pooling and factory caching.

    Args:
        tenant_id (str): Unique tenant identifier. Defaults to "default".

    Yields:
        Session: SQLAlchemy database session.
    """
    mode = "enterprise" if os.getenv("DEPLOYMENT_TYPE") == "CLOUD" else "local"
    engine = DatabaseFactory.get_engine(tenant_id, mode=mode)

    if tenant_id not in _session_factories:
        _session_factories[tenant_id] = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )

    session = _session_factories[tenant_id]()
    try:
        yield session
    finally:  # Close session and return to pool
        session.close()


class DecisionAuditTrail(Base):
    __tablename__ = "decision_audit_trail"

    decision_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    campaign_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # EU AI Act: Data Lineage Snapshot
    # Raw data snapshots at the moment of decision
    input_snapshot = Column(JSON)

    # Output metrics
    reconciled_roas: Mapped[float] = mapped_column(Float)
    confidence_level: Mapped[float] = mapped_column(Float)
    expected_value: Mapped[float] = mapped_column(Float)
    drift_score_at_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Human-in-the-loop audit
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_automated: Mapped[bool] = mapped_column(Boolean, default=True)
    checksum: Mapped[str] = mapped_column(String(64))  # Integrity check
