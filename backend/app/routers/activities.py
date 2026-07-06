"""活動記録（練習ログ）エンドポイント(#10)。

POST   /api/activities            — 活動記録を作成
GET    /api/activities            — 自分の活動記録一覧
GET    /api/activities/summary    — 期間サマリ
GET    /api/activities/{id}       — 活動記録詳細
PATCH  /api/activities/{id}       — 活動記録更新
DELETE /api/activities/{id}       — 活動記録削除

認証: 選手ロールのみ（自分の記録のみ操作可能）。
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AthleteOnly
from app.schemas.activity import (
    ActivityLogCreate,
    ActivityLogResponse,
    ActivityLogUpdate,
    ActivitySummaryResponse,
)
from app.services import activity_service

router = APIRouter()


@router.post(
    "",
    response_model=ActivityLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="活動記録を作成する",
)
def create_activity(
    req: ActivityLogCreate,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> ActivityLogResponse:
    """練習・試合・休養を記録する。選手ロールのみ。"""
    log = activity_service.create_activity(db, current_user, req)
    return ActivityLogResponse.model_validate(log)


@router.get(
    "",
    response_model=list[ActivityLogResponse],
    summary="自分の活動記録一覧を取得する",
)
def list_activities(
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
    date_from: date | None = Query(None, description="この日以降"),
    date_to: date | None = Query(None, description="この日以前"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ActivityLogResponse]:
    """活動記録を新しい順に取得する。日付範囲で絞り込み可能。"""
    logs = activity_service.list_activities(
        db, current_user, date_from=date_from, date_to=date_to, limit=limit, offset=offset
    )
    return [ActivityLogResponse.model_validate(log) for log in logs]


@router.get(
    "/summary",
    response_model=ActivitySummaryResponse,
    summary="活動サマリを取得する",
)
def get_summary(
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> ActivitySummaryResponse:
    """期間内の合計時間・平均疲労度・種別内訳を集計する。"""
    s = activity_service.get_summary(db, current_user, date_from=date_from, date_to=date_to)
    return ActivitySummaryResponse(
        total_count=s.total_count,
        total_duration_min=s.total_duration_min,
        avg_fatigue_level=s.avg_fatigue_level,
        practice_count=s.practice_count,
        match_count=s.match_count,
        rest_count=s.rest_count,
    )


@router.get(
    "/{activity_id}",
    response_model=ActivityLogResponse,
    summary="活動記録の詳細を取得する",
)
def get_activity(
    activity_id: uuid.UUID,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> ActivityLogResponse:
    """活動記録を 1 件取得する。本人のみ。"""
    log = activity_service.get_activity(db, current_user, activity_id)
    return ActivityLogResponse.model_validate(log)


@router.patch(
    "/{activity_id}",
    response_model=ActivityLogResponse,
    summary="活動記録を更新する",
)
def update_activity(
    activity_id: uuid.UUID,
    req: ActivityLogUpdate,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> ActivityLogResponse:
    """活動記録を更新する（指定フィールドのみ）。本人のみ。"""
    log = activity_service.update_activity(db, current_user, activity_id, req)
    return ActivityLogResponse.model_validate(log)


@router.delete(
    "/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="活動記録を削除する",
)
def delete_activity(
    activity_id: uuid.UUID,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """活動記録を削除する。本人のみ。"""
    activity_service.delete_activity(db, current_user, activity_id)
    return None
