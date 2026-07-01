"""AthleteProfile モデル — 選手プロフィール・公開設定。"""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AthleteProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    選手プロフィールテーブル。

    is_public=True の場合のみスカウトに公開される。
    未成年者（user.birth_date から計算）は user.parental_consent=True の場合のみ公開可能。
    """

    __tablename__ = "athlete_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # 基本情報
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str | None] = mapped_column(String(50), nullable=True)  # FW, MF, DF, GK 等
    sport: Mapped[str] = mapped_column(String(50), nullable=False, default="football")
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 都市・地域
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 身体データ
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 公開設定
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # pgvector 用の埋め込みベクトル（類似選手検索）
    # NOTE: pgvector 拡張が有効な環境のみ使用可。
    #       Vector 型は alembic migration で手動追加する。
    # embedding: Mapped[list[float] | None] = mapped_column(Vector(128), nullable=True)

    # リレーション
    user: Mapped["User"] = relationship("User", back_populates="athlete_profile")  # noqa: F821
    videos: Mapped[list["Video"]] = relationship(  # noqa: F821
        "Video",
        back_populates="athlete",
        cascade="all, delete-orphan",
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(  # noqa: F821
        "ActivityLog",
        back_populates="athlete",
        cascade="all, delete-orphan",
    )
    training_menus: Mapped[list["TrainingMenu"]] = relationship(  # noqa: F821
        "TrainingMenu",
        back_populates="athlete",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AthleteProfile id={self.id} name={self.name}>"
