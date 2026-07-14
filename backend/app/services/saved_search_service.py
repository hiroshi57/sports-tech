"""保存検索・新着アラートサービス(C#23)。

保存した条件に合致する公開選手のうち、last_checked_at 以降に
最新分析が付いたものを「新着」として数える。
mark_checked で既読化（last_checked_at を現在時刻に更新）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.saved_search import SavedSearch
from app.models.user import User
from app.models.video import AnalysisResult, Video, VideoStatus
from app.schemas.saved_search import SavedSearchCreate
from app.services import scout_service


@dataclass(frozen=True)
class SavedSearchWithCount:
    search: SavedSearch
    new_count: int


def create(db: Session, user: User, req: SavedSearchCreate) -> SavedSearch:
    s = SavedSearch(
        id=uuid.uuid4(),
        scout_user_id=user.id,
        name=req.name,
        position=req.position,
        sport=req.sport,
        location=req.location,
        min_total_score=req.min_total_score,
        last_checked_at=datetime.now(UTC),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def list_with_counts(db: Session, user: User) -> list[SavedSearchWithCount]:
    searches = list(
        db.execute(
            select(SavedSearch)
            .where(SavedSearch.scout_user_id == user.id)
            .order_by(SavedSearch.created_at.desc())
        ).scalars()
    )
    return [SavedSearchWithCount(search=s, new_count=_new_count(db, user, s)) for s in searches]


def delete(db: Session, user: User, search_id: uuid.UUID) -> None:
    s = _get_owned(db, user, search_id)
    db.delete(s)
    db.commit()


def mark_checked(db: Session, user: User, search_id: uuid.UUID) -> SavedSearch:
    s = _get_owned(db, user, search_id)
    s.last_checked_at = datetime.now(UTC)
    db.commit()
    db.refresh(s)
    return s


def _new_count(db: Session, user: User, s: SavedSearch) -> int:
    """条件に合致し、last_checked_at 以降に最新分析が付いた選手数。"""
    results = scout_service.search_athletes(
        db,
        position=s.position,
        sport=s.sport,
        location=s.location,
        min_total_score=s.min_total_score,
        limit=1000,
    )
    if s.last_checked_at is None:
        return len(results)

    baseline = s.last_checked_at
    if baseline.tzinfo is None:
        baseline = baseline.replace(tzinfo=UTC)

    count = 0
    for r in results:
        latest_at = _latest_analyzed_at(db, r.profile.id)
        if latest_at is not None:
            if latest_at.tzinfo is None:
                latest_at = latest_at.replace(tzinfo=UTC)
            if latest_at > baseline:
                count += 1
    return count


def _latest_analyzed_at(db: Session, athlete_id: uuid.UUID) -> datetime | None:
    return db.execute(
        select(AnalysisResult.created_at)
        .join(Video, AnalysisResult.video_id == Video.id)
        .where(Video.athlete_id == athlete_id)
        .where(Video.status == VideoStatus.COMPLETED)
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _get_owned(db: Session, user: User, search_id: uuid.UUID) -> SavedSearch:
    s = db.get(SavedSearch, search_id)
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="保存検索が見つかりません"
        )
    if s.scout_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="この保存検索へのアクセス権限がありません"
        )
    return s
