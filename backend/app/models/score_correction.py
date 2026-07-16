"""ScoreCorrection モデル(外販 A#9) — 誤判定の申告と人による補正ループ。

AIスコアに違和感がある場合、ユーザー（選手本人/コーチ/スカウト）が
「この結果はおかしい」と申告し、人手で補正値を提示できる。
承認されると補正が反映され、モデル改善のフィードバックデータにもなる。
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CorrectionStatus(str, enum.Enum):
    """補正申告のステータス。"""

    PENDING = "pending"  # 申告済み・レビュー待ち
    APPROVED = "approved"  # 承認・補正反映
    REJECTED = "rejected"  # 却下（元スコア維持）


class ScoreCorrection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AI分析結果に対する誤判定申告と補正提案。"""

    __tablename__ = "score_corrections"

    analysis_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # どのスコアが誤っているか（4基礎スコアのいずれか or total_score）
    metric: Mapped[str] = mapped_column(String(30), nullable=False)
    # 申告理由
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # 提案する補正値（任意。人手レビューで確定する場合は null）
    suggested_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[CorrectionStatus] = mapped_column(
        Enum(CorrectionStatus, name="correction_status"),
        nullable=False,
        default=CorrectionStatus.PENDING,
    )
    # レビュー結果
    resolved_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ScoreCorrection result={self.analysis_result_id} "
            f"metric={self.metric} status={self.status}>"
        )
