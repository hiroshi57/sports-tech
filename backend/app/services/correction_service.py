"""誤判定申告・補正ループ サービス(外販 A#9)。

- ユーザーがAI分析結果に対して補正を申告する
- レビュアー(コーチ/スカウト)が承認/却下し、承認時は補正値を確定する
- 承認された補正は AnalysisResult に反映され、モデル改善データにもなる
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.score_correction import CorrectionStatus, ScoreCorrection
from app.models.user import User, UserRole
from app.models.video import AnalysisResult

# 補正対象にできる指標
_VALID_METRICS = {
    "sprint_score",
    "ball_control_score",
    "positioning_score",
    "body_usage_score",
    "total_score",
}


def _validate_metric(metric: str) -> None:
    if metric not in _VALID_METRICS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"補正対象の指標が不正です: {metric}",
        )


def submit_correction(
    db: Session,
    reporter: User,
    analysis_result_id: uuid.UUID,
    metric: str,
    reason: str,
    suggested_value: float | None,
) -> ScoreCorrection:
    """誤判定を申告する。"""
    _validate_metric(metric)
    result = db.get(AnalysisResult, analysis_result_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="対象の分析結果が見つかりません",
        )
    if suggested_value is not None and not (0.0 <= suggested_value <= 100.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="補正値は0〜100の範囲で指定してください",
        )
    correction = ScoreCorrection(
        id=uuid.uuid4(),
        analysis_result_id=analysis_result_id,
        reporter_user_id=reporter.id,
        metric=metric,
        reason=reason,
        suggested_value=suggested_value,
        status=CorrectionStatus.PENDING,
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)
    return correction


def list_corrections(
    db: Session,
    *,
    analysis_result_id: uuid.UUID | None = None,
    status_filter: CorrectionStatus | None = None,
) -> list[ScoreCorrection]:
    """補正申告を一覧する。"""
    stmt = select(ScoreCorrection)
    if analysis_result_id is not None:
        stmt = stmt.where(ScoreCorrection.analysis_result_id == analysis_result_id)
    if status_filter is not None:
        stmt = stmt.where(ScoreCorrection.status == status_filter)
    stmt = stmt.order_by(ScoreCorrection.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def review_correction(
    db: Session,
    reviewer: User,
    correction_id: uuid.UUID,
    *,
    approve: bool,
    resolved_value: float | None = None,
    reviewer_note: str | None = None,
) -> ScoreCorrection:
    """補正申告をレビューする。承認時は AnalysisResult に補正を反映する。

    レビューはコーチ/スカウトのみ実施可能。
    """
    if reviewer.role not in (UserRole.COACH, UserRole.SCOUT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="補正のレビューはコーチ/スカウトのみ可能です",
        )
    correction = db.get(ScoreCorrection, correction_id)
    if correction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="対象の補正申告が見つかりません",
        )
    if correction.status != CorrectionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この申告はすでにレビュー済みです",
        )

    if approve:
        final_value = resolved_value if resolved_value is not None else correction.suggested_value
        if final_value is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="承認には補正値(resolved_value か suggested_value)が必要です",
            )
        if not (0.0 <= final_value <= 100.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="補正値は0〜100の範囲で指定してください",
            )
        # AnalysisResult に反映
        result = db.get(AnalysisResult, correction.analysis_result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="対象の分析結果が見つかりません",
            )
        setattr(result, correction.metric, final_value)
        db.add(result)

        correction.status = CorrectionStatus.APPROVED
        correction.resolved_value = final_value
    else:
        correction.status = CorrectionStatus.REJECTED

    correction.resolved_at = datetime.now(UTC)
    correction.reviewer_note = reviewer_note
    db.add(correction)
    db.commit()
    db.refresh(correction)
    return correction
