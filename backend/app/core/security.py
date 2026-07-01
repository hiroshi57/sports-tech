"""JWT トークン生成・検証・パスワードハッシュ。

Supabase Auth との統合を想定し、JWT の検証ロジックを提供する。
ローカル開発では HS256 形式の自前 JWT を使用する。
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt によるパスワードハッシュ（将来のパスワード認証用）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """平文パスワードを bcrypt でハッシュ化する。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """平文パスワードとハッシュを照合する。"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    role: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    JWT アクセストークンを生成する。

    Args:
        subject: ユーザー ID (UUID 文字列)
        role: ユーザーロール ("athlete" | "scout" | "coach")
        extra_claims: 追加クレーム（任意）
        expires_delta: 有効期限（省略時は設定値を使用）

    Returns:
        エンコードされた JWT 文字列
    """
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": datetime.now(UTC),
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    JWT トークンをデコードし、クレームを返す。

    Raises:
        JWTError: トークンが無効または期限切れの場合
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def is_token_valid(token: str) -> bool:
    """トークンが有効かどうかを判定する（例外を発生させない）。"""
    try:
        decode_access_token(token)
        return True
    except JWTError:
        return False
