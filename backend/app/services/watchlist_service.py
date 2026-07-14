"""ウォッチリストサービス(C#22)。

スカウト/コーチが選手をお気に入り登録し、メモ・タグで管理する。
公開/未成年同意チェックは scout_service を再利用する。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.athlete import AthleteProfile
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.services import scout_service


@dataclass(frozen=True)
class WatchlistEntry:
    item: WatchlistItem
    profile: AthleteProfile
    latest_total_score: float | None


def add(
    db: Session,
    user: User,
    athlete_id: uuid.UUID,
    note: str | None = None,
    tags: str | None = None,
) -> WatchlistEntry:
    """選手をウォッチリストに追加する（公開選手のみ・重複時は既存を更新）。"""
    # 公開/閲覧可否チェック（404 は scout_service 側で送出）
    detail = scout_service.get_athlete_detail(db, athlete_id, user)

    existing = db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.scout_user_id == user.id)
        .where(WatchlistItem.athlete_id == athlete_id)
    ).scalar_one_or_none()

    if existing is not None:
        if note is not None:
            existing.note = note
        if tags is not None:
            existing.tags = tags
        db.commit()
        db.refresh(existing)
        item = existing
    else:
        item = WatchlistItem(
            id=uuid.uuid4(),
            scout_user_id=user.id,
            athlete_id=athlete_id,
            note=note,
            tags=tags,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

    return WatchlistEntry(
        item=item, profile=detail.profile, latest_total_score=detail.latest_total_score
    )


def list_items(db: Session, user: User) -> list[WatchlistEntry]:
    """自分のウォッチリストを新しい順で返す。"""
    items = list(
        db.execute(
            select(WatchlistItem)
            .where(WatchlistItem.scout_user_id == user.id)
            .order_by(WatchlistItem.created_at.desc())
        ).scalars()
    )
    entries: list[WatchlistEntry] = []
    for it in items:
        profile = db.get(AthleteProfile, it.athlete_id)
        if profile is None:
            continue
        latest = scout_service._latest_total_score(db, profile.id)
        entries.append(WatchlistEntry(item=it, profile=profile, latest_total_score=latest))
    return entries


def update(
    db: Session, user: User, item_id: uuid.UUID, note: str | None, tags: str | None
) -> WatchlistEntry:
    """メモ・タグを更新する。"""
    item = _get_owned(db, user, item_id)
    if note is not None:
        item.note = note
    if tags is not None:
        item.tags = tags
    db.commit()
    db.refresh(item)
    profile = db.get(AthleteProfile, item.athlete_id)
    latest = scout_service._latest_total_score(db, item.athlete_id) if profile else None
    return WatchlistEntry(item=item, profile=profile, latest_total_score=latest)


def remove(db: Session, user: User, item_id: uuid.UUID) -> None:
    """ウォッチリストから削除する。"""
    item = _get_owned(db, user, item_id)
    db.delete(item)
    db.commit()


def _get_owned(db: Session, user: User, item_id: uuid.UUID) -> WatchlistItem:
    item = db.get(WatchlistItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="項目が見つかりません")
    if item.scout_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="この項目へのアクセス権限がありません"
        )
    return item
