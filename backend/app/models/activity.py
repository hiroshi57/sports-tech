"""ActivityLog / SelfCareRecord モデル — 活動記録・セルフケア。"""

import enum
import uuid
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ActivityType(str, enum.Enum):
    """活動種別。"""

    PRACTICE = "practice"  # 練習
    MATCH = "match"  # 試合
    REST = "rest"  # 休養


class ActivityLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    活動記録テーブル。

    日々の練習・試合・休養を記録する。
    疲労度スコアはセルフケア機能でリスク判定に使用される。
    """

    __tablename__ = "activity_logs"

    __table_args__ = (
        CheckConstraint("fatigue_level BETWEEN 1 AND 5", name="ck_fatigue_level_range"),
        CheckConstraint("duration_min >= 0", name="ck_duration_min_positive"),
    )

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    activity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activity_type"),
        nullable=False,
    )
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 分
    fatigue_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1〜5
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # リレーション
    athlete: Mapped["AthleteProfile"] = relationship(  # noqa: F821
        "AthleteProfile",
        back_populates="activity_logs",
    )

    def __repr__(self) -> str:
        return (
            f"<ActivityLog athlete_id={self.athlete_id} "
            f"date={self.activity_date} type={self.activity_type}>"
        )


class SelfCareRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    セルフケア記録テーブル。

    栄養・睡眠・体重などの健康データを管理する。
    怪我リスクスコア計算の入力として使用される。
    """

    __tablename__ = "self_care_records"

    __table_args__ = (
        CheckConstraint("sleep_hours BETWEEN 0 AND 24", name="ck_sleep_hours_range"),
        CheckConstraint("injury_risk_score BETWEEN 0 AND 100", name="ck_injury_risk_range"),
    )

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # 睡眠
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 体重（kg）
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 栄養メモ
    nutrition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 怪我リスクスコア（AI計算値 0〜100 / 高いほどリスク高）
    injury_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # リスクアラートを送信済みか
    alert_sent: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<SelfCareRecord athlete_id={self.athlete_id} date={self.record_date}>"
