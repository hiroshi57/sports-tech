"""スコア品質・信頼性関連スキーマ(外販 A#5/#7/#9)。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── A#7 プロ水準リファレンス ──────────────────────────────────────


class ProReferenceResponse(BaseModel):
    """プロ水準基準への到達度。"""

    position: str
    reference: dict[str, float]
    attainment: dict[str, float]
    overall_attainment: float
    gap: dict[str, float]
    is_reference_score: bool = True


# ── A#5 バイアス監査 ──────────────────────────────────────────────


class SegmentStatResponse(BaseModel):
    segment: str
    sample_size: int
    mean_total: float
    delta_from_overall: float
    low_sample: bool
    flagged: bool


class BiasAuditResponse(BaseModel):
    overall_mean: float
    overall_sample: int
    by_age: list[SegmentStatResponse]
    by_build: list[SegmentStatResponse]
    notes: list[str]


# ── A#9 補正ループ ────────────────────────────────────────────────


class CorrectionCreate(BaseModel):
    """誤判定の申告。"""

    analysis_result_id: uuid.UUID
    metric: str = Field(
        ...,
        description="補正対象の指標(sprint/ball_control/positioning/body_usage/total の各 _score)",
    )
    reason: str = Field(..., min_length=1, max_length=1000)
    suggested_value: float | None = Field(None, ge=0, le=100)


class CorrectionReview(BaseModel):
    """補正申告のレビュー。"""

    approve: bool
    resolved_value: float | None = Field(None, ge=0, le=100)
    reviewer_note: str | None = Field(None, max_length=1000)


class CorrectionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    analysis_result_id: uuid.UUID
    reporter_user_id: uuid.UUID
    metric: str
    reason: str
    suggested_value: float | None
    status: str
    resolved_value: float | None
    resolved_at: datetime | None
    reviewer_note: str | None
    created_at: datetime
