"""スコア品質・信頼性エンドポイント(外販 A#5/#7/#9)。

GET  /api/quality/pro-reference          — プロ水準リファレンスDB(全ポジション)
GET  /api/quality/bias-audit             — バイアス監査レポート
POST /api/quality/corrections            — 誤判定を申告する
GET  /api/quality/corrections            — 補正申告一覧
POST /api/quality/corrections/{id}/review— 補正をレビュー(コーチ/スカウト)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentUser, ScoutOrCoach
from app.models.score_correction import CorrectionStatus
from app.schemas.quality import (
    BiasAuditResponse,
    CorrectionCreate,
    CorrectionResponse,
    CorrectionReview,
    ProReferenceResponse,
    SegmentStatResponse,
)
from app.services import bias_audit, correction_service, pro_reference

router = APIRouter()


@router.get(
    "/pro-reference",
    response_model=list[ProReferenceResponse],
    summary="プロ水準リファレンスDB(全ポジション)を取得する",
)
def get_pro_reference() -> list[ProReferenceResponse]:
    """ポジション別のプロ水準基準（到達度100%の理想像）を返す。"""
    out: list[ProReferenceResponse] = []
    for pos, prof in pro_reference.all_profiles().items():
        ev = pro_reference.evaluate(pos, prof)
        out.append(
            ProReferenceResponse(
                position=ev.position,
                reference=ev.reference,
                attainment=ev.attainment,
                overall_attainment=ev.overall_attainment,
                gap=ev.gap,
            )
        )
    return out


@router.get(
    "/bias-audit",
    response_model=BiasAuditResponse,
    summary="バイアス監査レポートを取得する",
)
def get_bias_audit(
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> BiasAuditResponse:
    """年代・体格セグメント別の総合スコア分布と不均衡を監査する。"""
    report = bias_audit.run_audit(db)
    return BiasAuditResponse(
        overall_mean=report.overall_mean,
        overall_sample=report.overall_sample,
        by_age=[SegmentStatResponse(**vars(s)) for s in report.by_age],
        by_build=[SegmentStatResponse(**vars(s)) for s in report.by_build],
        notes=report.notes,
    )


@router.post(
    "/corrections",
    response_model=CorrectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="誤判定を申告する",
)
def submit_correction(
    req: CorrectionCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CorrectionResponse:
    c = correction_service.submit_correction(
        db,
        current_user,
        req.analysis_result_id,
        req.metric,
        req.reason,
        req.suggested_value,
    )
    return CorrectionResponse.model_validate(c)


@router.get(
    "/corrections",
    response_model=list[CorrectionResponse],
    summary="補正申告を一覧する",
)
def list_corrections(
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
    analysis_result_id: uuid.UUID | None = Query(None),
    status_filter: CorrectionStatus | None = Query(None, alias="status"),
) -> list[CorrectionResponse]:
    items = correction_service.list_corrections(
        db, analysis_result_id=analysis_result_id, status_filter=status_filter
    )
    return [CorrectionResponse.model_validate(c) for c in items]


@router.post(
    "/corrections/{correction_id}/review",
    response_model=CorrectionResponse,
    summary="補正申告をレビューする(コーチ/スカウト)",
)
def review_correction(
    correction_id: uuid.UUID,
    req: CorrectionReview,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> CorrectionResponse:
    c = correction_service.review_correction(
        db,
        current_user,
        correction_id,
        approve=req.approve,
        resolved_value=req.resolved_value,
        reviewer_note=req.reviewer_note,
    )
    return CorrectionResponse.model_validate(c)
