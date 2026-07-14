"""ウォッチリストスキーマ(C#22)。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WatchlistAddRequest(BaseModel):
    """ウォッチリスト追加リクエスト。"""

    athlete_id: uuid.UUID
    note: str | None = Field(None, max_length=2000)
    tags: str | None = Field(None, max_length=300)


class WatchlistUpdateRequest(BaseModel):
    """メモ・タグの更新。"""

    note: str | None = Field(None, max_length=2000)
    tags: str | None = Field(None, max_length=300)


class WatchlistItemResponse(BaseModel):
    """ウォッチリスト項目（選手要約 + メモ/タグ + 最新総合スコア）。"""

    id: uuid.UUID
    athlete_id: uuid.UUID
    name: str
    position: str | None
    sport: str
    location: str | None
    latest_total_score: float | None
    note: str | None
    tags: str | None
    created_at: datetime
    is_reference_score: bool = True
