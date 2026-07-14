"""保存検索・新着アラートエンドポイント(C#23)。

GET    /api/scouts/saved-searches            — 一覧（新着件数付き）
POST   /api/scouts/saved-searches            — 保存
POST   /api/scouts/saved-searches/{id}/check — 新着を既読化
DELETE /api/scouts/saved-searches/{id}       — 削除

認証: スカウト/コーチのみ。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import ScoutOrCoach
from app.schemas.saved_search import SavedSearchCreate, SavedSearchResponse
from app.services import saved_search_service
from app.services.saved_search_service import SavedSearchWithCount

router = APIRouter()


def _to_response(sc: SavedSearchWithCount) -> SavedSearchResponse:
    s = sc.search
    return SavedSearchResponse(
        id=s.id,
        name=s.name,
        position=s.position,
        sport=s.sport,
        location=s.location,
        min_total_score=s.min_total_score,
        last_checked_at=s.last_checked_at,
        new_count=sc.new_count,
        created_at=s.created_at,
    )


@router.get("", response_model=list[SavedSearchResponse], summary="保存検索一覧（新着件数付き）")
def list_saved(
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> list[SavedSearchResponse]:
    return [_to_response(sc) for sc in saved_search_service.list_with_counts(db, current_user)]


@router.post(
    "",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="検索条件を保存する",
)
def create_saved(
    req: SavedSearchCreate,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> SavedSearchResponse:
    s = saved_search_service.create(db, current_user, req)
    return _to_response(SavedSearchWithCount(search=s, new_count=0))


@router.post(
    "/{search_id}/check",
    response_model=SavedSearchResponse,
    summary="新着を既読化する",
)
def check_saved(
    search_id: uuid.UUID,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> SavedSearchResponse:
    s = saved_search_service.mark_checked(db, current_user, search_id)
    return _to_response(SavedSearchWithCount(search=s, new_count=0))


@router.delete(
    "/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="保存検索を削除する",
)
def delete_saved(
    search_id: uuid.UUID,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    saved_search_service.delete(db, current_user, search_id)
    return None
