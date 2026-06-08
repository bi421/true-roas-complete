"""
Subscription management for TrueROAS.
Handles plan activation, status tracking, and lifecycle events.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Any, cast

from sqlalchemy import Column, DateTime, Enum as SQLEnum, String, Integer, func, Boolean
from sqlalchemy.orm import Session
import secrets

from .database import Base


class TenantStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"


class SubscriptionTier(str, Enum):
    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"
    CORE = "CORE"


class Tenant(Base):
    """
    Central Metadata for Multi-Tenant Orchestration.
    """

    __tablename__ = "tenants"

    uuid = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(64), nullable=False, unique=True, index=True)
    sqlite_path = Column(String(1024), nullable=False)  # Validated absolute path
    tenant_secret_salt = Column(String(64), nullable=False)
    mfa_secret = Column(String(255), nullable=True)  # Encrypted TOTP secret
    stripe_customer_id = Column(String(255), nullable=True, unique=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    status: Any = Column(
        SQLEnum(TenantStatus), default=TenantStatus.PENDING, nullable=False
    )
    subscription_tier: Any = Column(SQLEnum(SubscriptionTier), nullable=False)
    do_not_track = Column(Boolean, default=False, nullable=False)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)

    # Compliance: Opt-in for automated campaign management (ads_management permission)
    auto_pause_enabled = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    canceled_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Aggregated Marketing Email Stats (PII-free)
    email_opens = Column(Integer, default=0)
    email_clicks = Column(Integer, default=0)
    email_bounces = Column(Integer, default=0)

    def is_active(self) -> bool:
        """Check if subscription allows system access."""
        return cast(
            bool,
            self.status == TenantStatus.ACTIVE
            and (
                self.current_period_end is None
                or self.current_period_end > datetime.utcnow()
            ),
        )

    def __repr__(self) -> str:
        return f"<Tenant(slug={self.slug}, status={self.status}, tier={self.subscription_tier})>"


class SubscriptionService:
    """Business logic for subscription lifecycle."""

    @staticmethod
    def create_subscription(
        db: Session,
        tenant_id: str,
        plan_type: SubscriptionTier,
        stripe_customer_id: Optional[str] = None,
    ) -> Tenant:
        """Create new subscription record. Idempotent if exists."""
        existing = db.query(Tenant).filter(Tenant.slug == tenant_id).first()

        if existing:
            if existing.status != TenantStatus.SUSPENDED:
                raise ValueError(f"Active subscription exists for tenant {tenant_id}")

            existing.status = TenantStatus.PENDING
            existing.subscription_tier = plan_type
            existing.stripe_customer_id = (
                str(stripe_customer_id) if stripe_customer_id else None  # type: ignore[assignment]
            )
            existing.status = TenantStatus.PENDING
            existing.subscription_tier = plan_type
            existing.stripe_customer_id = (
                str(stripe_customer_id) if stripe_customer_id else None  # type: ignore[assignment]
            )

            existing.canceled_at = None  # type: ignore[assignment]
            db.commit()
            return existing

        sub = Tenant(
            slug=tenant_id,
            name=f"Prospect {tenant_id}",  # Default name for new prospects
            subscription_tier=plan_type,
            stripe_customer_id=stripe_customer_id,
            tenant_secret_salt=secrets.token_urlsafe(32),
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return sub

    @staticmethod
    def activate_subscription(
        db: Session,
        tenant_id: str,
        admin_email: str,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        plan_type: SubscriptionTier,
        period_start: datetime,
        period_end: datetime,
    ) -> Tenant:
        """Activate after successful payment."""
        sub = (
            db.query(Tenant).filter(Tenant.slug == tenant_id).with_for_update().first()
        )

        if not sub:
            sub = Tenant(
                slug=tenant_id,
                name=tenant_id,
                sqlite_path=f"./data/tenants/{tenant_id}.db",
                tenant_secret_salt=secrets.token_urlsafe(32),
            )
            db.add(sub)

        sub.status = TenantStatus.ACTIVE
        sub.admin_email = admin_email  # type: ignore[assignment]
        sub.subscription_tier = plan_type
        sub.stripe_customer_id = stripe_customer_id  # type: ignore[assignment]
        sub.stripe_subscription_id = stripe_subscription_id  # type: ignore[assignment]
        sub.current_period_start = period_start  # type: ignore[assignment]
        sub.current_period_end = period_end  # type: ignore[assignment]
        db.commit()
        db.refresh(sub)
        return sub

    @staticmethod
    def mark_past_due(db: Session, tenant_id: str) -> Tenant:
        """Mark subscription past due after failed payment."""
        sub = (
            db.query(Tenant).filter(Tenant.slug == tenant_id).with_for_update().first()
        )

        if not sub:
            raise ValueError(f"No subscription found for tenant {tenant_id}")

        sub.status = TenantStatus.SUSPENDED
        db.commit()
        db.refresh(sub)
        return sub

    @staticmethod
    def cancel_subscription(db: Session, tenant_id: str) -> Tenant:
        """Cancel subscription (immediate or at period end)."""
        sub = (
            db.query(Tenant).filter(Tenant.slug == tenant_id).with_for_update().first()
        )

        if not sub:
            raise ValueError(f"No subscription found for tenant {tenant_id}")

        sub.status = TenantStatus.SUSPENDED
        sub.canceled_at = datetime.utcnow()  # type: ignore[assignment]
        db.commit()
        db.refresh(sub)
        return sub
