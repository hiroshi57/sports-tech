"""活動記録（練習ログ）サービス(#10)。

選手が自分の練習・試合・休養を記録・閲覧・編集・削除する。
すべて選手本人のプロフィールに紐づき、他人の記録にはアクセスできない。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity import ActivityLog, ActivityType
from app.models.athlete import AthleteProfile
from app.models.user import User
from app.schemas.activity import ActivityLogCreate, ActivityLogUpdate


@dataclass(frozen=True)
class ActivitySummary:
    total_count: int
    total_duration_min: int
    avg_fatigue_level: float | None
    practice_count: int
    match_count: int
    rest_count: int


def _get_profile(db: Session, user: User) -> AthleteProfile:
    """ユーザーに紐づく選手プロフィールを取得する。"""
    profile = db.execute(
        select(AthleteProfile).where(AthleteProfile.user_id == user.id)
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="選手プロフィールが未登録です。先にプロフィールを作成してください。",
        )
    return profile


def create_activity(db: Session, user: User, req: ActivityLogCreate) -> ActivityLog:
    """活動記録を作成する。"""
    profile = _get_profile(db, user)
    log = ActivityLog(
        id=uuid.uuid4(),
        athlete_id=profile.id,
        activity_date=req.activity_date,
        activity_type=req.activity_type,
        duration_min=req.duration_min,
        fatigue_level=req.fatigue_level,
        notes=req.notes,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_activities(
    db: Session,
    user: User,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ActivityLog]:
    """自分の活動記録一覧を取得する（新しい順）。"""
    profile = _get_profile(db, user)
    stmt = select(ActivityLog).where(ActivityLog.athlete_id == profile.id)
    if date_from is not None:
        stmt = stmt.where(ActivityLog.activity_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(ActivityLog.activity_date <= date_to)
    stmt = stmt.order_by(ActivityLog.activity_date.desc(), ActivityLog.created_at.desc())
    stmt = stmt.limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


def get_activity(db: Session, user: User, activity_id: uuid.UUID) -> ActivityLog:
    """自分の活動記録を 1 件取得する。"""
    return _get_owned_activity(db, user, activity_id)


def update_activity(
    db: Session, user: User, activity_id: uuid.UUID, req: ActivityLogUpdate
) -> ActivityLog:
    """活動記録を更新する（指定フィールドのみ）。"""
    log = _get_owned_activity(db, user, activity_id)
    data = req.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(log, field, value)
    db.commit()
    db.refresh(log)
    return log


def delete_activity(db: Session, user: User, activity_id: uuid.UUID) -> None:
    """活動記録を削除する。"""
    log = _get_owned_activity(db, user, activity_id)
    db.delete(log)
    db.commit()


def get_summary(
    db: Session,
    user: User,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ActivitySummary:
    """期間内の活動サマリを集計する。"""
    profile = _get_profile(db, user)
    base = select(ActivityLog).where(ActivityLog.athlete_id == profile.id)
    if date_from is not None:
        base = base.where(ActivityLog.activity_date >= date_from)
    if date_to is not None:
        base = base.where(ActivityLog.activity_date <= date_to)

    subq = base.subquery()
    row = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(subq.c.duration_min), 0),
            func.avg(subq.c.fatigue_level),
        ).select_from(subq)
    ).one()
    total_count, total_duration, avg_fatigue = row

    def _count_type(t: ActivityType) -> int:
        stmt = select(func.count()).select_from(subq).where(subq.c.activity_type == t)
        return db.execute(stmt).scalar_one()

    return ActivitySummary(
        total_count=int(total_count),
        total_duration_min=int(total_duration),
        avg_fatigue_level=round(float(avg_fatigue), 2) if avg_fatigue is not None else None,
        practice_count=_count_type(ActivityType.PRACTICE),
        match_count=_count_type(ActivityType.MATCH),
        rest_count=_count_type(ActivityType.REST),
    )


def _get_owned_activity(db: Session, user: User, activity_id: uuid.UUID) -> ActivityLog:
    """指定 ID の活動記録を取得し、本人所有か検証する。"""
    profile = _get_profile(db, user)
    log = db.get(ActivityLog, activity_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="活動記録が見つかりません",
        )
    if log.athlete_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この活動記録へのアクセス権限がありません",
        )
    return log
