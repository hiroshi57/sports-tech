"""認証関連スキーマ。"""

from datetime import date

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole

_MINOR_AGE_THRESHOLD = 18


class RegisterRequest(BaseModel):
    """ユーザー登録リクエスト。"""

    email: EmailStr
    role: UserRole = UserRole.ATHLETE
    birth_date: date | None = None
    parental_consent: bool = False

    @field_validator("parental_consent")
    @classmethod
    def validate_minor_consent(cls, v: bool, info: object) -> bool:
        """18歳未満は parental_consent=True が必須。"""
        data = getattr(info, "data", {})
        birth_date: date | None = data.get("birth_date")
        if birth_date is not None:
            age = (date.today() - birth_date).days // 365
            if age < _MINOR_AGE_THRESHOLD and not v:
                msg = "18歳未満は parental_consent=true が必要です"
                raise ValueError(msg)
        return v


class LoginRequest(BaseModel):
    """ログインリクエスト（メール＋パスワード形式、ローカル開発用）。"""

    email: EmailStr
    # 本番は Supabase Auth が担うため、ここでは email のみで識別する
    # password フィールドは将来の拡張のため定義だけ残す
    # password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """トークンレスポンス。"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒


class MeResponse(BaseModel):
    """現在ユーザー情報レスポンス。"""

    model_config = {"from_attributes": True}

    id: str
    email: str
    role: UserRole
    is_active: bool
    parental_consent: bool
