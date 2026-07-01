"""FastAPI 共通 Dependency。

認証・認可に関する Depends を集約する。
各エンドポイントは必要なものだけを import して使う。
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

# Bearer トークン抽出（Authorization: Bearer <token>）
_bearer = HTTPBearer(auto_error=True)


def _get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict:
    """Authorization ヘッダーから JWT を取り出してデコードする。"""
    try:
        return decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンが無効または期限切れです",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    payload: Annotated[dict, Depends(_get_token_payload)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    JWT から現在のユーザーを取得する。

    Raises:
        401: トークンの sub が不正
        401: ユーザーが存在しない
        403: アカウントが無効化されている
    """
    raw_sub = payload.get("sub")
    if not raw_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンのペイロードが不正です",
        )

    try:
        user_id = uuid.UUID(raw_sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの subject が不正な UUID です",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが存在しません",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効化されています",
        )
    return user


# ── ロール検証 Dependency ファクトリ ──────────────────────────────────


def require_role(*roles: UserRole):
    """
    指定ロールのいずれかを持つユーザーのみ通過させる Dependency。

    Usage:
        @router.get("/scout/search")
        def search(user: Annotated[User, Depends(require_role(UserRole.SCOUT))]):
            ...
    """

    def _check(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"この操作には {[r.value for r in roles]} ロールが必要です",
            )
        return current_user

    return _check


# ── 型エイリアス（各ルーターで使いやすくする） ─────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]
ScoutOrCoach = Annotated[User, Depends(require_role(UserRole.SCOUT, UserRole.COACH))]
AthleteOnly = Annotated[User, Depends(require_role(UserRole.ATHLETE))]
