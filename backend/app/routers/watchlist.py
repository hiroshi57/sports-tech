"""ウォッチリストエンドポイント(C#22)。

GET    /api/scouts/watchlist       — 自分のウォッチリスト
POST   /api/scouts/watchlist       — 追加（重複時はメモ/タグ更新）
PATCH  /api/scouts/watchlist/{id}  — メモ/タグ更新
DELETE /api/scouts/watchlist/{id}  — 削除

認証: スカウト/コーチのみ。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import ScoutOrCoach
from app.schemas.watchlist import (
    WatchlistAddRequest,
    WatchlistItemResponse,
    WatchlistUpdateRequest,
)
from app.services import watchlist_service
from app.services.watchlist_service import WatchlistEntry

router = APIRouter()


def _to_response(e: WatchlistEntry) -> WatchlistItemResponse:
    return WatchlistItemResponse(
        id=e.item.id,
        athlete_id=e.profile.id,
        name=e.profile.name,
        position=e.profile.position,
        sport=e.profile.sport,
        location=e.profile.location,
        latest_total_score=e.latest_total_score,
        note=e.item.note,
        tags=e.item.tags,
        created_at=e.item.created_at,
    )


@router.get("", response_model=list[WatchlistItemResponse], summary="ウォッチリストを取得する")
def list_watchlist(
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> list[WatchlistItemResponse]:
    return [_to_response(e) for e in watchlist_service.list_items(db, current_user)]


@router.post(
    "",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="ウォッチリストに追加する",
)
def add_watchlist(
    req: WatchlistAddRequest,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> WatchlistItemResponse:
    entry = watchlist_service.add(db, current_user, req.athlete_id, req.note, req.tags)
    return _to_response(entry)


@router.patch(
    "/{item_id}",
    response_model=WatchlistItemResponse,
    summary="メモ・タグを更新する",
)
def update_watchlist(
    item_id: uuid.UUID,
    req: WatchlistUpdateRequest,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> WatchlistItemResponse:
    entry = watchlist_service.update(db, current_user, item_id, req.note, req.tags)
    return _to_response(entry)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="ウォッチリストから削除する",
)
def remove_watchlist(
    item_id: uuid.UUID,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    watchlist_service.remove(db, current_user, item_id)
    return None
