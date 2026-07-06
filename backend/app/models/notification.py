"""Notification モデル(#19) — アプリ内通知。

分析完了・スカウト閲覧・怪我リスクアラート等をユーザーに通知する。
Push / メール送信は Phase 2 でこのレコードを起点に配信する。
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NotificationType(str, enum.Enum):
    """通知種別。"""

    ANALYSIS_COMPLETED = "analysis_completed"  # 動画分析が完了した
    ANALYSIS_FAILED = "analysis_failed"  # 動画分析が失敗した
    SCOUT_VIEWED = "scout_viewed"  # スカウトがプロフィールを閲覧した
    INJURY_RISK_ALERT = "injury_risk_alert"  # 怪我リスクが高い


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """アプリ内通知テーブル。"""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 関連リソース（動画ID等）を任意で保持する
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.type} read={self.is_read}>"
