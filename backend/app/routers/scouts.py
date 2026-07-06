"""スカウト向け選手検索エンドポイント(#15)。

GET /api/scouts/athletes         — 公開選手を条件検索
GET /api/scouts/athletes/{id}    — 公開選手の詳細

認証: スカウト or コーチロールのみ。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import ScoutOrCoach
from app.schemas.athlete import AthleteSearchItem
from app.services import scout_service
from app.services.scout_service import AthleteSearchResult

router = APIRouter()


def _to_item(result: AthleteSearchResult) -> AthleteSearchItem:
    p = result.profile
    return AthleteSearchItem(
        id=p.id,
        name=p.name,
        position=p.position,
        sport=p.sport,
        location=p.location,
        height_cm=p.height_cm,
        weight_kg=p.weight_kg,
        latest_total_score=result.latest_total_score,
    )


@router.get(
    "/athletes",
    response_model=list[AthleteSearchItem],
    summary="公開選手を条件検索する",
)
def search_athletes(
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
    position: str | None = Query(None, description="ポジション（FW/MF/DF/GK 等・完全一致）"),
    sport: str | None = Query(None, description="競技（完全一致）"),
    location: str | None = Query(None, description="地域（部分一致）"),
    min_total_score: float | None = Query(None, ge=0, le=100, description="総合スコア下限"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[AthleteSearchItem]:
    """
    公開設定（is_public=True）の選手を検索する。

    未成年者は保護者同意がある場合のみ結果に含まれる。
    スコアは参考値（is_reference_score: true）。
    """
    results = scout_service.search_athletes(
        db,
        position=position,
        sport=sport,
        location=location,
        min_total_score=min_total_score,
        limit=limit,
        offset=offset,
    )
    return [_to_item(r) for r in results]


@router.get(
    "/athletes/{athlete_id}",
    response_model=AthleteSearchItem,
    summary="公開選手の詳細を取得する",
)
def get_athlete(
    athlete_id: uuid.UUID,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> AthleteSearchItem:
    """公開選手の詳細。非公開・未成年同意なしは 404。"""
    result = scout_service.get_athlete_detail(db, athlete_id, current_user)
    return _to_item(result)
