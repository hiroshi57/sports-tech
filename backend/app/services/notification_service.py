"""通知サービス(#19)。

アプリ内通知の作成・取得・既読管理。
Push / メール配信は Phase 2 でこのレコードを起点に行う。
"""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    body: str | None = None,
    resource_id: uuid.UUID | None = None,
) -> Notification:
    """通知を作成する（サービス内部・ワーカーから呼ぶ）。"""
    notification = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        resource_id=resource_id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_notifications(
    db: Session,
    user_id: uuid.UUID,
    *,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    """ユーザーの通知一覧を取得する（新しい順）。"""
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


def count_unread(db: Session, user_id: uuid.UUID) -> int:
    """未読通知数を返す。"""
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id)
        .where(Notification.is_read.is_(False))
    )
    return int(db.execute(stmt).scalar_one())


def mark_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    """通知を既読にする（本人のみ）。"""
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知が見つかりません",
        )
    if notification.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この通知へのアクセス権限がありません",
        )
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
    """全通知を既読にする。既読にした件数を返す。"""
    unread = list_notifications(db, user_id, unread_only=True, limit=1000)
    for n in unread:
        n.is_read = True
    db.commit()
    return len(unread)


def notify_analysis_completed(db: Session, user_id: uuid.UUID, video_id: uuid.UUID) -> None:
    """分析完了通知を作成する（ワーカーから呼ぶ、失敗しても本処理は止めない）。"""
    try:
        create_notification(
            db,
            user_id=user_id,
            type=NotificationType.ANALYSIS_COMPLETED,
            title="動画の分析が完了しました",
            body="ホーム画面から分析結果（参考スコア）を確認できます。",
            resource_id=video_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("分析完了通知の作成に失敗（video=%s）: %s", video_id, exc)


def notify_analysis_failed(db: Session, user_id: uuid.UUID, video_id: uuid.UUID) -> None:
    """分析失敗通知を作成する。"""
    try:
        create_notification(
            db,
            user_id=user_id,
            type=NotificationType.ANALYSIS_FAILED,
            title="動画の分析に失敗しました",
            body="お手数ですが、動画を再アップロードしてください。",
            resource_id=video_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("分析失敗通知の作成に失敗（video=%s）: %s", video_id, exc)
