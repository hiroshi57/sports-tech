"""User モデル — 認証・ロール管理。"""

import enum
from datetime import date

from sqlalchemy import Boolean, Date, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    """ユーザーロール。"""

    ATHLETE = "athlete"
    SCOUT = "scout"
    COACH = "coach"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    ユーザーテーブル。

    Supabase Auth で発行された UUID を id として使用する。
    ロールによって利用できる機能が異なる。
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.ATHLETE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 未成年者保護: 保護者同意フラグ（18歳未満は True が必要）
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    parental_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # リレーション
    athlete_profile: Mapped["AthleteProfile | None"] = relationship(  # noqa: F821
        "AthleteProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
