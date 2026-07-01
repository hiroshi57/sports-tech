"""認証エンドポイント。

POST /api/auth/register  — 新規登録
POST /api/auth/login     — ログイン（JWT 取得）
GET  /api/auth/me        — 現在ユーザー情報
POST /api/auth/logout    — ログアウト（クライアント側でトークン破棄）
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.services import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新規ユーザー登録",
)
def register(
    req: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """
    新規ユーザーを登録し、JWT アクセストークンを返す。

    - 18歳未満の場合は `parental_consent: true` が必須
    - メールアドレスの重複は 409 Conflict を返す
    """
    user, token = auth_service.register_user(db, req)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="ログイン（JWT 取得）",
)
def login(
    req: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """
    登録済みユーザーの JWT アクセストークンを発行する。

    Note:
        本番環境では Supabase Auth が認証を担う。
        このエンドポイントはローカル開発・テスト用の簡易実装。
    """
    user, token = auth_service.login_user(db, req)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="現在のユーザー情報を取得",
)
def me(current_user: CurrentUser) -> MeResponse:
    """
    JWT から現在ログイン中のユーザー情報を返す。

    Authorization: Bearer <token> が必要。
    """
    return MeResponse(
        id=str(current_user.id),
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        parental_consent=current_user.parental_consent,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="ログアウト",
)
def logout(current_user: CurrentUser) -> None:
    """
    ログアウト。

    JWT はステートレスなため、サーバー側での処理はなし。
    クライアント側でトークンを破棄すること。
    将来的には Redis ブラックリストでトークン無効化を実装する。
    """
    return None
