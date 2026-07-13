"""Video / AnalysisResult モデル — 動画管理・AI分析結果。"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VideoStatus(str, enum.Enum):
    """動画処理ステータス。"""

    PENDING = "pending"  # アップロード済み・分析待ち
    PROCESSING = "processing"  # 分析中
    COMPLETED = "completed"  # 分析完了
    FAILED = "failed"  # 分析失敗


class Video(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    動画テーブル。

    選手がアップロードした練習動画のメタデータを管理する。
    実体は S3 に保存し、s3_key でアクセスする。
    """

    __tablename__ = "videos"

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # S3 オブジェクトキー（例: "videos/athlete-uuid/2026-07-01/xxx.mp4"）
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 動画メタデータ
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 秒
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False, default="video/mp4")

    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, name="video_status"),
        nullable=False,
        default=VideoStatus.PENDING,
        index=True,
    )

    # Celery タスク ID（分析ジョブ追跡用）
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 保存期間管理（D#35）: 最終アクセス日時。満了判定の起点。
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 満了予告通知の送信済みフラグ（重複通知防止）
    retention_warned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # リレーション
    athlete: Mapped["AthleteProfile"] = relationship(  # noqa: F821
        "AthleteProfile",
        back_populates="videos",
    )
    analysis_result: Mapped["AnalysisResult | None"] = relationship(
        "AnalysisResult",
        back_populates="video",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Video id={self.id} status={self.status}>"


class AnalysisResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    AI分析結果テーブル。

    各スコアは 0〜100 の範囲。
    スコアは「参考値」であり確定評価ではない（UI で明示すること）。
    """

    __tablename__ = "analysis_results"

    __table_args__ = (
        CheckConstraint("sprint_score BETWEEN 0 AND 100", name="ck_sprint_score_range"),
        CheckConstraint("ball_control_score BETWEEN 0 AND 100", name="ck_ball_control_score_range"),
        CheckConstraint("positioning_score BETWEEN 0 AND 100", name="ck_positioning_score_range"),
        CheckConstraint("body_usage_score BETWEEN 0 AND 100", name="ck_body_usage_score_range"),
        CheckConstraint("total_score BETWEEN 0 AND 100", name="ck_total_score_range"),
    )

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # 能力スコア（各 0〜100）
    sprint_score: Mapped[float] = mapped_column(Float, nullable=False)
    ball_control_score: Mapped[float] = mapped_column(Float, nullable=False)
    positioning_score: Mapped[float] = mapped_column(Float, nullable=False)
    body_usage_score: Mapped[float] = mapped_column(Float, nullable=False)

    # 総合スコア（加重平均）
    total_score: Mapped[float] = mapped_column(Float, nullable=False)

    # 信頼度（0.0〜1.0 / 動画品質・解析精度による）
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # AIフィードバックテキスト
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # リレーション
    video: Mapped["Video"] = relationship("Video", back_populates="analysis_result")

    def __repr__(self) -> str:
        return f"<AnalysisResult video_id={self.video_id} total={self.total_score}>"
