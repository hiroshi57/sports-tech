"""WatchlistItem モデル(外販 C#22) — スカウトのお気に入り選手。

スカウト/コーチが気になる選手を保存し、メモ・タグを付けて管理する。
(scout_user_id, athlete_id) で一意。
"""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WatchlistItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """スカウトのウォッチリスト項目。"""

    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("scout_user_id", "athlete_id", name="uq_watchlist_scout_athlete"),
    )

    scout_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 任意のメモ・タグ（カンマ区切り）
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(300), nullable=True)

    def __repr__(self) -> str:
        return f"<WatchlistItem scout={self.scout_user_id} athlete={self.athlete_id}>"
