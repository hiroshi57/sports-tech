"""スカウトCRM系モデル(外販 C#25-27, C#30)。

- ContactLog: 選手への接触ログ・商談パイプライン(C#25)
- AthleteNote: チーム内での選手共有コメント(C#26)
- VideoClip: 動画クリップの切り出し・共有(C#27)
- ProfileViewLog: スカウト閲覧履歴（選手側へ開示, C#30）
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContactStage(str, enum.Enum):
    """商談パイプラインのステージ。"""

    INTERESTED = "interested"  # 注目
    CONTACTED = "contacted"  # 接触済み
    TRIAL = "trial"  # 練習参加・トライアル
    OFFER = "offer"  # オファー提示
    SIGNED = "signed"  # 獲得
    DROPPED = "dropped"  # 見送り


class ContactLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """選手への接触ログ・商談パイプライン(C#25)。"""

    __tablename__ = "contact_logs"

    scout_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    athlete_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[ContactStage] = mapped_column(
        Enum(ContactStage, name="contact_stage"),
        nullable=False,
        default=ContactStage.INTERESTED,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ContactLog scout={self.scout_user_id} "
            f"athlete={self.athlete_profile_id} stage={self.stage}>"
        )


class AthleteNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """チーム内での選手共有コメント(C#26)。

    同一組織のスカウト/コーチ間で選手への所見を共有する。
    Phase 1 は全スカウト/コーチに公開（組織アカウント E#40 導入時にスコープ制限）。
    """

    __tablename__ = "athlete_notes"

    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    athlete_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"<AthleteNote author={self.author_user_id} athlete={self.athlete_profile_id}>"


class VideoClip(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """動画クリップの切り出し・共有(C#27)。

    元動画の区間(start/end 秒)をメタデータとして保存し、再生時に区間指定する。
    物理的な切り出し（トランスコード）は行わず軽量に共有する。
    """

    __tablename__ = "video_clips"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<VideoClip video={self.video_id} {self.start_sec}-{self.end_sec}s>"


class ProfileViewLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """スカウトによる選手カルテ閲覧ログ(C#30)。

    選手側に「誰に見られたか」を開示し、透明性を担保する（監査ログ）。
    """

    __tablename__ = "profile_view_logs"

    viewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    athlete_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<ProfileViewLog viewer={self.viewer_user_id} athlete={self.athlete_profile_id}>"
