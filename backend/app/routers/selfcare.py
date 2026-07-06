"""セルフケアエンドポイント(#13/#14)。

POST /api/selfcare/records      — セルフケア記録を作成
GET  /api/selfcare/records      — 自分のセルフケア記録一覧
GET  /api/selfcare/injury-risk  — 現在の怪我リスク推定

認証: 選手ロールのみ。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AthleteOnly
from app.schemas.selfcare import (
    InjuryRiskResponse,
    SelfCareRecordCreate,
    SelfCareRecordResponse,
)
from app.services import selfcare_service

router = APIRouter()


@router.post(
    "/records",
    response_model=SelfCareRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="セルフケア記録を作成する",
)
def create_record(
    req: SelfCareRecordCreate,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> SelfCareRecordResponse:
    """睡眠・体重・栄養を記録し、その時点の怪我リスクを保存する。"""
    record = selfcare_service.create_record(db, current_user, req)
    return SelfCareRecordResponse.model_validate(record)


@router.get(
    "/records",
    response_model=list[SelfCareRecordResponse],
    summary="自分のセルフケア記録一覧を取得する",
)
def list_records(
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[SelfCareRecordResponse]:
    """セルフケア記録を新しい順に取得する。"""
    records = selfcare_service.list_records(db, current_user, limit=limit, offset=offset)
    return [SelfCareRecordResponse.model_validate(r) for r in records]


@router.get(
    "/injury-risk",
    response_model=InjuryRiskResponse,
    summary="現在の怪我リスクを推定する",
)
def get_injury_risk(
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> InjuryRiskResponse:
    """
    活動記録・セルフケア記録から怪我リスク（0〜100）を推定する。

    参考値であり医療診断ではない。痛みや不調は専門家に相談すること。
    """
    risk = selfcare_service.get_injury_risk(db, current_user)
    return InjuryRiskResponse(
        risk_score=risk.risk_score,
        risk_level=risk.risk_level,
        factors=risk.factors,
        acwr=risk.acwr,
    )
