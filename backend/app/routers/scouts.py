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
from app.schemas.athlete import (
    AthleteScoresResponse,
    AthleteSearchItem,
    GrowthPredictionResponse,
    MetricBenchmark,
    ScoreSnapshot,
)
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


def _to_snapshot(r) -> ScoreSnapshot:
    return ScoreSnapshot(
        sprint_score=r.sprint_score,
        ball_control_score=r.ball_control_score,
        positioning_score=r.positioning_score,
        body_usage_score=r.body_usage_score,
        total_score=r.total_score,
        analyzed_at=r.created_at,
    )


@router.get(
    "/athletes/{athlete_id}/scores",
    response_model=AthleteScoresResponse,
    summary="公開選手のスコア詳細（最新+履歴）を取得する",
)
def get_athlete_scores(
    athlete_id: uuid.UUID,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> AthleteScoresResponse:
    """
    レーダーチャート・履歴グラフ用の詳細スコアを返す。

    スコアは参考値（is_reference_score: true）。
    """
    profile, latest, history = scout_service.get_athlete_scores(db, athlete_id, current_user)
    analytics = scout_service.compute_analytics(db, profile, latest, history)
    bench = analytics.benchmark

    # 成長予測(B#20): 履歴（古い順）とオーナーの生年月日から算出
    prediction = None
    if latest is not None:
        from app.models.user import User
        from app.services import growth_service

        owner = db.get(User, profile.user_id)
        totals_oldest_first = [r.total_score for r in reversed(history)]
        gp = growth_service.predict(
            totals_oldest_first,
            latest.total_score,
            owner.birth_date if owner else None,
        )
        prediction = GrowthPredictionResponse(
            horizon=gp.horizon,
            projected_total=gp.projected_total,
            potential=gp.potential,
            monthly_trend=gp.monthly_trend,
            comment=gp.comment,
        )

    return AthleteScoresResponse(
        id=profile.id,
        name=profile.name,
        position=profile.position,
        sport=profile.sport,
        location=profile.location,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        latest=_to_snapshot(latest) if latest is not None else None,
        history=[_to_snapshot(r) for r in reversed(history)],  # 古い順（履歴グラフ用）
        benchmark=MetricBenchmark(
            sprint_score=bench.sprint_score,
            ball_control_score=bench.ball_control_score,
            positioning_score=bench.positioning_score,
            body_usage_score=bench.body_usage_score,
            total_score=bench.total_score,
            sample_size=bench.sample_size,
        )
        if bench is not None
        else None,
        percentile=analytics.percentile,
        consistency=analytics.consistency,
        bmi=analytics.bmi,
        prediction=prediction,
    )
