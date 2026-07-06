"""セルフケア（怪我リスク・栄養・睡眠）スキーマ(#13/#14)。"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class SelfCareRecordCreate(BaseModel):
    """セルフケア記録の作成リクエスト。"""

    record_date: date
    sleep_hours: float | None = Field(None, ge=0, le=24)
    weight_kg: float | None = Field(None, gt=0, le=300)
    nutrition_notes: str | None = Field(None, max_length=2000)


class SelfCareRecordResponse(BaseModel):
    """セルフケア記録レスポンス。"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    record_date: date
    sleep_hours: float | None
    weight_kg: float | None
    nutrition_notes: str | None
    injury_risk_score: float | None
    created_at: datetime
    updated_at: datetime


class InjuryRiskResponse(BaseModel):
    """怪我リスク推定レスポンス。

    Note:
        リスクスコアは参考値です。医療的診断ではありません。
        痛みや不調がある場合は専門家に相談してください。
    """

    risk_score: float = Field(..., ge=0, le=100, description="怪我リスク（0=低〜100=高）")
    risk_level: str = Field(..., description="low / moderate / high")
    factors: list[str] = Field(default_factory=list, description="リスク要因の説明")
    acwr: float | None = Field(None, description="急性:慢性 負荷比（1.5超で高リスク）")
    is_reference_score: bool = True
