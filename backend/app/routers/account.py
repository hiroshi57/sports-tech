"""アカウント（開示・削除）エンドポイント(外販 D #33)。

GET    /api/account/export — 本人データの開示（JSON エクスポート）
DELETE /api/account        — 本人アカウントと関連データの削除

認証: 全ロール（本人のみ）。
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.services import account_service

router = APIRouter()


@router.get("/export", summary="本人データを開示（エクスポート）する")
def export_account(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """本人に紐づく全データを JSON で返す（個人情報開示請求対応）。"""
    return account_service.export_account(db, current_user)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="本人アカウントと関連データを削除する",
)
def delete_account(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """本人アカウントを削除する。関連データも連鎖削除される（削除請求対応）。"""
    account_service.delete_account(db, current_user)
    return None
