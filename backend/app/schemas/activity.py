"""活動記録（練習ログ）スキーマ(#10)。"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.activity import ActivityType


class ActivityLogCreate(BaseModel):
    """活動記録の作成リクエスト。"""

    activity_date: date
    activity_type: ActivityType
    duration_min: int = Field(0, ge=0, le=1440, description="活動時間（分・0〜1440）")
    fatigue_level: int = Field(..., ge=1, le=5, description="疲労度（1=軽い〜5=非常に重い）")
    notes: str | None = Field(None, max_length=2000)


class ActivityLogUpdate(BaseModel):
    """活動記録の更新リクエスト（全フィールド任意）。"""

    activity_date: date | None = None
    activity_type: ActivityType | None = None
    duration_min: int | None = Field(None, ge=0, le=1440)
    fatigue_level: int | None = Field(None, ge=1, le=5)
    notes: str | None = Field(None, max_length=2000)


class ActivityLogResponse(BaseModel):
    """活動記録レスポンス。"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    activity_date: date
    activity_type: ActivityType
    duration_min: int
    fatigue_level: int
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ActivitySummaryResponse(BaseModel):
    """一定期間の活動サマリ（セルフケア・振り返りの土台）。"""

    total_count: int
    total_duration_min: int
    avg_fatigue_level: float | None
    practice_count: int
    match_count: int
    rest_count: int
