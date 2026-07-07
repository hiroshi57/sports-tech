"""練習振り返りスキーマ(#12)。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    """振り返り作成リクエスト。"""

    video_id: uuid.UUID | None = None
    self_rating: int | None = Field(None, ge=1, le=5)
    went_well: str | None = Field(None, max_length=2000)
    to_improve: str | None = Field(None, max_length=2000)
    notes: str | None = Field(None, max_length=2000)


class ReviewUpdate(BaseModel):
    """振り返り更新リクエスト（全フィールド任意）。"""

    self_rating: int | None = Field(None, ge=1, le=5)
    went_well: str | None = Field(None, max_length=2000)
    to_improve: str | None = Field(None, max_length=2000)
    notes: str | None = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    """振り返りレスポンス。"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    video_id: uuid.UUID | None
    self_rating: int | None
    went_well: str | None
    to_improve: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
