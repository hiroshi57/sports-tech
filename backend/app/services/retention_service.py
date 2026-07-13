"""動画の保存期間管理サービス(D#35)。

- 満了予告: 満了 N 日前に選手へ通知（重複防止）
- 満了削除: 保存期間を過ぎた動画の S3 実体 + レコードを削除（分析結果は残す）

保存期間・予告日数は設定で変更可能（プラン別対応の余地）。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import s3 as s3_client
from app.models.athlete import AthleteProfile
from app.models.video import Video, VideoStatus

logger = logging.getLogger(__name__)

# 既定の保存期間（日）— 24ヶ月
DEFAULT_RETENTION_DAYS = 730
# 満了予告を出すリードタイム（日）
WARN_BEFORE_DAYS = 14


@dataclass(frozen=True)
class RetentionResult:
    warned_video_ids: list[uuid.UUID]
    deleted_video_ids: list[uuid.UUID]


def _reference_time(v: Video) -> datetime:
    """満了判定の基準時刻（last_accessed_at 優先、無ければ created_at）。"""
    return v.last_accessed_at or v.created_at


def touch(db: Session, video: Video) -> None:
    """動画アクセス時に最終アクセス日時を更新し、予告フラグを解除する。"""
    video.last_accessed_at = datetime.now(UTC)
    video.retention_warned = False
    db.commit()


def process_retention(
    db: Session,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    warn_before_days: int = WARN_BEFORE_DAYS,
    now: datetime | None = None,
) -> RetentionResult:
    """
    保存期間の予告・削除を実行する（日次バッチから呼ぶ）。

    - 満了 <= warn_before_days 日前 かつ 未予告 → 予告通知して retention_warned=True
    - 満了超過 → S3削除 + Videoレコード削除（AnalysisResult は残る）
    """
    from app.services import notification_service

    now = now or datetime.now(UTC)
    expiry_delta = timedelta(days=retention_days)
    warn_delta = timedelta(days=retention_days - warn_before_days)

    warned: list[uuid.UUID] = []
    deleted: list[uuid.UUID] = []

    videos = list(db.execute(select(Video).where(Video.status != VideoStatus.PROCESSING)).scalars())

    for v in videos:
        ref = _reference_time(v)
        # tz 未指定の created_at 対策
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)
        age = now - ref

        if age >= expiry_delta:
            # 満了 → 削除
            try:
                s3_client.delete_s3_object(v.s3_key)
            except Exception as exc:  # noqa: BLE001
                logger.warning("retention: S3削除失敗 video=%s: %s", v.id, exc)
            vid = v.id
            db.delete(v)
            deleted.append(vid)
        elif age >= warn_delta and not v.retention_warned:
            # 予告
            user_id = _resolve_user_id(db, v.athlete_id)
            if user_id is not None:
                _notify_expiring(notification_service, db, user_id, v.id)
            v.retention_warned = True
            warned.append(v.id)

    db.commit()
    return RetentionResult(warned_video_ids=warned, deleted_video_ids=deleted)


def _resolve_user_id(db: Session, athlete_id: uuid.UUID) -> uuid.UUID | None:
    profile = db.get(AthleteProfile, athlete_id)
    return profile.user_id if profile is not None else None


def _notify_expiring(notification_service, db: Session, user_id: uuid.UUID, video_id: uuid.UUID):
    from app.models.notification import NotificationType

    try:
        notification_service.create_notification(
            db,
            user_id=user_id,
            type=NotificationType.ANALYSIS_COMPLETED,  # 汎用通知として利用
            title="まもなく動画の保存期間が満了します",
            body="保存期間満了後は動画が自動削除されます（分析スコアは保持されます）。",
            resource_id=video_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("retention: 予告通知失敗 video=%s: %s", video_id, exc)
