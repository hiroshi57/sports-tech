"""練習メニュースキーマ(#11)。"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExerciseItem(BaseModel):
    """ドリル 1 件。"""

    name: str
    duration_min: int = Field(..., ge=0)
    description: str | None = None
    target_skill: str | None = None  # sprint / ball_control / positioning / body_usage


class TrainingMenuResponse(BaseModel):
    """練習メニューレスポンス。"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    title: str
    description: str | None
    is_ai_generated: bool
    total_duration_min: int
    difficulty: str
    exercises: list[dict[str, Any]]
    created_at: datetime


class GenerateMenuRequest(BaseModel):
    """AI メニュー生成リクエスト。"""

    target_duration_min: int = Field(60, ge=15, le=180, description="希望する練習時間（分）")
