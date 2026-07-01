"""TrainingMenu モデル — 練習メニュー管理。"""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TrainingMenu(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    練習メニューテーブル。

    AI推薦またはコーチ・選手が手動作成した練習メニュー。
    exercises は JSON 配列で柔軟なドリル構成を保持する。
    """

    __tablename__ = "training_menus"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI生成フラグ（True=AI推薦 / False=手動作成）
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 合計予定時間（分）
    total_duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 難易度: beginner / intermediate / advanced / elite
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="intermediate")

    # ドリル一覧（JSON 配列）
    # 例: [{"name": "コーンドリブル", "duration_min": 10, "description": "...", "video_url": null}]
    exercises: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    # リレーション
    athlete: Mapped["AthleteProfile"] = relationship(  # noqa: F821
        "AthleteProfile",
        back_populates="training_menus",
    )

    def __repr__(self) -> str:
        return f"<TrainingMenu id={self.id} title={self.title}>"
