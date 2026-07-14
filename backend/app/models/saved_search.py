"""SavedSearch モデル(外販 C#23) — スカウトの保存済み検索条件。

保存した条件に新しく合致した公開選手を「新着」として検知する。
last_checked_at 以降に分析が付いた（=検索対象になった）選手を新着として数える。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SavedSearch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """スカウトの保存検索条件。"""

    __tablename__ = "saved_searches"

    scout_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 検索条件（すべて任意）
    position: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sport: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    min_total_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 新着判定の基準時刻（この時刻以降に条件を満たした選手を新着とみなす）
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<SavedSearch scout={self.scout_user_id} name={self.name}>"
