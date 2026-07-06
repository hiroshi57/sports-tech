"""スカウト向け選手検索サービス(#15)。

公開設定（is_public=True）の選手のみを検索対象とする。
未成年者は保護者同意（user.parental_consent=True）がある場合のみ公開する。
スカウトによる閲覧は監査ログ（#40）で追跡する想定（本サービスでは検索のみ）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.athlete import AthleteProfile
from app.models.user import User
from app.models.video import AnalysisResult, Video, VideoStatus

# 未成年判定のしきい値（歳）
MINOR_AGE_THRESHOLD = 18


@dataclass(frozen=True)
class AthleteSearchResult:
    """検索結果 1 件（プロフィール + 最新総合スコア）。"""

    profile: AthleteProfile
    latest_total_score: float | None


def _calc_age(birth_date: date | None, today: date | None = None) -> int | None:
    if birth_date is None:
        return None
    today = today or date.today()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def _is_publicly_visible(profile: AthleteProfile, user: User) -> bool:
    """
    スカウトに公開してよい選手か判定する。

    - is_public=False は非公開
    - 未成年（<18）は parental_consent=True の場合のみ公開
    """
    if not profile.is_public:
        return False
    age = _calc_age(user.birth_date)
    if age is not None and age < MINOR_AGE_THRESHOLD and not user.parental_consent:
        return False
    return True


def search_athletes(
    db: Session,
    *,
    position: str | None = None,
    sport: str | None = None,
    location: str | None = None,
    min_total_score: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[AthleteSearchResult]:
    """
    公開選手を条件で検索する。

    Args:
        position/sport/location: 部分一致 or 完全一致フィルタ
        min_total_score: 最新分析の総合スコア下限
        limit/offset: ページネーション

    Returns:
        AthleteSearchResult のリスト（総合スコア降順 → 名前昇順）
    """
    stmt = (
        select(AthleteProfile, User)
        .join(User, AthleteProfile.user_id == User.id)
        .where(AthleteProfile.is_public.is_(True))
    )

    if position:
        stmt = stmt.where(AthleteProfile.position == position)
    if sport:
        stmt = stmt.where(AthleteProfile.sport == sport)
    if location:
        stmt = stmt.where(AthleteProfile.location.ilike(f"%{location}%"))

    rows = db.execute(stmt).all()

    results: list[AthleteSearchResult] = []
    for profile, user in rows:
        if not _is_publicly_visible(profile, user):
            continue
        latest = _latest_total_score(db, profile.id)
        if min_total_score is not None and (latest is None or latest < min_total_score):
            continue
        results.append(AthleteSearchResult(profile=profile, latest_total_score=latest))

    # 総合スコア降順（None は最後）→ 名前昇順
    results.sort(key=lambda r: (-(r.latest_total_score or -1.0), r.profile.name))
    return results[offset : offset + limit]


def get_athlete_detail(db: Session, athlete_id: uuid.UUID, user: User) -> AthleteSearchResult:
    """
    公開選手の詳細を取得する。

    Raises:
        404: 選手が存在しない / 非公開
    """
    profile = db.get(AthleteProfile, athlete_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="選手が見つかりません",
        )
    owner = db.get(User, profile.user_id)
    if owner is None or not _is_publicly_visible(profile, owner):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="選手が見つかりません",
        )
    return AthleteSearchResult(
        profile=profile,
        latest_total_score=_latest_total_score(db, profile.id),
    )


def _latest_total_score(db: Session, athlete_id: uuid.UUID) -> float | None:
    """選手の最新（完了済み）分析の総合スコアを返す。"""
    stmt = (
        select(AnalysisResult.total_score)
        .join(Video, AnalysisResult.video_id == Video.id)
        .where(Video.athlete_id == athlete_id)
        .where(Video.status == VideoStatus.COMPLETED)
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()
