"""通知エンドポイント(#19)。

GET   /api/notifications              — 自分の通知一覧
GET   /api/notifications/unread-count — 未読数
POST  /api/notifications/{id}/read    — 既読にする
POST  /api/notifications/read-all     — 全既読

認証: 全ロール（本人の通知のみ）。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.notification import NotificationResponse, UnreadCountResponse
from app.services import notification_service

router = APIRouter()


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="自分の通知一覧を取得する",
)
def list_notifications(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[NotificationResponse]:
    """通知を新しい順に取得する。"""
    items = notification_service.list_notifications(
        db, current_user.id, unread_only=unread_only, limit=limit, offset=offset
    )
    return [NotificationResponse.model_validate(n) for n in items]


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="未読通知数を取得する",
)
def unread_count(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UnreadCountResponse:
    """未読の通知数を返す（バッジ表示用）。"""
    return UnreadCountResponse(unread_count=notification_service.count_unread(db, current_user.id))


@router.post(
    "/read-all",
    response_model=UnreadCountResponse,
    summary="全通知を既読にする",
)
def read_all(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UnreadCountResponse:
    """全通知を既読にし、既読にした件数を返す。"""
    count = notification_service.mark_all_read(db, current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="通知を既読にする",
)
def mark_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> NotificationResponse:
    """指定した通知を既読にする。本人のみ。"""
    n = notification_service.mark_read(db, current_user.id, notification_id)
    return NotificationResponse.model_validate(n)
