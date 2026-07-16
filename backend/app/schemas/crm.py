"""スカウトCRM系スキーマ(外販 C#25-30)。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

# ── C#25: 接触ログ・パイプライン ──────────────────────────────────


class ContactLogCreate(BaseModel):
    athlete_profile_id: uuid.UUID
    stage: str = Field("interested", description="interested/contacted/trial/offer/signed/dropped")
    note: str | None = Field(None, max_length=2000)
    contacted_at: datetime | None = None


class ContactLogUpdate(BaseModel):
    stage: str | None = None
    note: str | None = Field(None, max_length=2000)
    contacted_at: datetime | None = None


class ContactLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_profile_id: uuid.UUID
    stage: str
    note: str | None
    contacted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PipelineSummary(BaseModel):
    """パイプラインのステージ別件数。"""

    stage: str
    count: int


# ── C#26: 共有ノート ──────────────────────────────────────────────


class AthleteNoteCreate(BaseModel):
    athlete_profile_id: uuid.UUID
    body: str = Field(..., min_length=1, max_length=4000)


class AthleteNoteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    author_user_id: uuid.UUID
    athlete_profile_id: uuid.UUID
    body: str
    created_at: datetime


# ── C#27: 動画クリップ ────────────────────────────────────────────


class VideoClipCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    start_sec: float = Field(..., ge=0)
    end_sec: float = Field(..., gt=0)
    comment: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _check_range(self) -> VideoClipCreate:
        if self.end_sec <= self.start_sec:
            raise ValueError("end_sec は start_sec より大きい必要があります")
        return self


class VideoClipResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    video_id: uuid.UUID
    creator_user_id: uuid.UUID
    title: str
    start_sec: float
    end_sec: float
    comment: str | None
    created_at: datetime


# ── C#28: 類似選手 ────────────────────────────────────────────────


class SimilarAthleteResponse(BaseModel):
    athlete_id: uuid.UUID
    name: str
    position: str | None
    similarity: float
    total_score: float
    is_reference_score: bool = True


# ── C#29: 市場価値 ────────────────────────────────────────────────


class MarketValueResponse(BaseModel):
    low_jpy: int
    high_jpy: int
    age_factor: float
    position_factor: float
    comment: str
    is_reference_score: bool = True


# ── C#30: 閲覧ログ（選手側開示） ──────────────────────────────────


class ProfileViewResponse(BaseModel):
    viewer_role: str  # scout / coach（個人特定を避けロールのみ開示）
    viewed_at: datetime


class ProfileViewSummary(BaseModel):
    total_views: int
    views_last_30d: int
    recent: list[ProfileViewResponse]
