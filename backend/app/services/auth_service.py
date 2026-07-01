"""認証サービス — ユーザー登録・ログイン・未成年者チェック。

Supabase Auth との統合を将来的に想定し、現状はローカル JWT 方式で動作する。
Supabase を有効にする場合は verify_supabase_token() を差し替える。
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest

# 未成年者の年齢閾値
_MINOR_AGE_THRESHOLD = 18


def _calculate_age(birth_date: date) -> int:
    """誕生日から現在の年齢を計算する。"""
    today = date.today()
    return (today - birth_date).days // 365


def _validate_minor_consent(birth_date: date | None, parental_consent: bool) -> None:
    """未成年者（18歳未満）の保護者同意を検証する。"""
    if birth_date is None:
        return
    age = _calculate_age(birth_date)
    if age < _MINOR_AGE_THRESHOLD and not parental_consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="18歳未満の方はアカウント登録に保護者の同意が必要です",
        )


def register_user(db: Session, req: RegisterRequest) -> tuple[User, str]:
    """
    新規ユーザーを登録し、アクセストークンを返す。

    Args:
        db: DB セッション
        req: 登録リクエスト

    Returns:
        (User オブジェクト, JWT アクセストークン)

    Raises:
        422: 未成年者で保護者同意なし
        409: メールアドレスが既に使用されている
    """
    _validate_minor_consent(req.birth_date, req.parental_consent)

    user = User(
        id=uuid.uuid4(),
        email=req.email,
        role=req.role,
        birth_date=req.birth_date,
        parental_consent=req.parental_consent,
        is_active=True,
        # パスワードハッシュ（将来のパスワード認証用フィールドに格納）
        # 現状は Supabase Auth が認証を担うため、ハッシュは保存しない
        # _password_hash=hash_password(req.password) if req.password else None,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このメールアドレスは既に登録されています",
        )

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return user, token


def login_user(db: Session, req: LoginRequest) -> tuple[User, str]:
    """
    メールアドレスでユーザーを検索し、アクセストークンを返す。

    Note:
        本番環境では Supabase Auth が認証を担う。
        このメソッドはローカル開発・テスト用の簡易実装。

    Raises:
        401: ユーザーが存在しない、または無効化されている
    """
    from sqlalchemy import select

    stmt = select(User).where(User.email == req.email)
    user = db.execute(stmt).scalar_one_or_none()

    if user is None or not user.is_active:
        # セキュリティ: ユーザーの存在有無を明かさない
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return user, token


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """ID でユーザーを取得する。"""
    return db.get(User, user_id)


def deactivate_user(db: Session, user: User) -> User:
    """ユーザーアカウントを無効化する（論理削除）。"""
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
