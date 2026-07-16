"""Subscription モデル(外販 E#37) — ユーザーの契約プランと当期利用量。

1ユーザー1サブスクリプション。未作成のユーザーは FREE 相当として扱う。
Stripe 連携用の customer/subscription ID と、当期の利用カウンタを持つ。
請求書払い(B2B)の場合は billing_type=INVOICE でカード不要。
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SubscriptionStatus(str, enum.Enum):
    """契約ステータス。"""

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"  # 支払い遅延
    CANCELED = "canceled"


class BillingType(str, enum.Enum):
    """支払い方法。"""

    CARD = "card"  # Stripe カード決済
    INVOICE = "invoice"  # 請求書払い（B2B）


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """ユーザーの契約プランと当期利用量。"""

    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # プラン区分（billing_plans.PlanTier の value）
    plan_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    billing_type: Mapped[BillingType] = mapped_column(
        Enum(BillingType, name="billing_type"),
        nullable=False,
        default=BillingType.CARD,
    )

    # Stripe 連携
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 当期の利用カウンタ（period_start でリセット）
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analyses_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<Subscription user={self.user_id} plan={self.plan_tier} status={self.status}>"
