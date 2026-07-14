"""保存検索スキーマ(C#23)。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SavedSearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    position: str | None = Field(None, max_length=50)
    sport: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=100)
    min_total_score: float | None = Field(None, ge=0, le=100)


class SavedSearchResponse(BaseModel):
    id: uuid.UUID
    name: str
    position: str | None
    sport: str | None
    location: str | None
    min_total_score: float | None
    last_checked_at: datetime | None
    new_count: int  # last_checked_at 以降に条件を満たした新着選手数
    created_at: datetime
