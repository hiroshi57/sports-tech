"""User スキーマ — API リクエスト/レスポンス定義。"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    """ユーザー作成リクエスト。"""

    email: EmailStr
    role: UserRole = UserRole.ATHLETE
    birth_date: date | None = None
    parental_consent: bool = False

    @field_validator("parental_consent")
    @classmethod
    def validate_minor_consent(cls, v: bool, info: object) -> bool:
        """18歳未満は parental_consent=True が必須。"""
        # birth_date が渡された場合のみチェック
        data = getattr(info, "data", {})
        birth_date = data.get("birth_date")
        if birth_date is not None:
            age = (date.today() - birth_date).days // 365
            if age < 18 and not v:
                raise ValueError("未成年者（18歳未満）は保護者同意フラグが必要です")
        return v


class UserResponse(BaseModel):
    """ユーザー情報レスポンス。"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    parental_consent: bool
    created_at: datetime
