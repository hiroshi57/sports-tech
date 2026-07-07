"""PracticeReview モデル(#12) — 練習振り返り。

動画（＋そのAI分析スコア）に対して、選手やコーチが振り返りコメントと
自己評価を記録する。動画・スコアとレビューを結びつけ、成長を追跡する。
"""

import uuid

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PracticeReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """練習振り返りテーブル。"""

    __tablename__ = "practice_reviews"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 振り返り対象の動画（任意 — 動画なしの振り返りも許可）
    video_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 自己評価（1〜5）
    self_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # うまくいった点
    went_well: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 改善したい点
    to_improve: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 自由記述メモ
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PracticeReview id={self.id} athlete_id={self.athlete_id}>"
