"""AthleteProfile スキーマ。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AthleteProfileCreate(BaseModel):
    """選手プロフィール作成リクエスト。"""

    name: str = Field(..., min_length=1, max_length=100)
    position: str | None = Field(None, max_length=50)
    sport: str = Field("football", max_length=50)
    location: str | None = Field(None, max_length=100)
    bio: str | None = None
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=300)
    is_public: bool = False


class AthleteProfileUpdate(BaseModel):
    """選手プロフィール更新リクエスト（全フィールド任意）。"""

    name: str | None = Field(None, min_length=1, max_length=100)
    position: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=100)
    bio: str | None = None
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=300)
    is_public: bool | None = None


class AthleteProfileResponse(BaseModel):
    """選手プロフィールレスポンス。"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    position: str | None
    sport: str
    location: str | None
    bio: str | None
    height_cm: float | None
    weight_kg: float | None
    is_public: bool
    created_at: datetime
    updated_at: datetime


class AthleteProfileSummary(BaseModel):
    """スカウト検索向け要約レスポンス（個人情報を最小化）。"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    position: str | None
    sport: str
    location: str | None
    is_public: bool


class AthleteSearchItem(BaseModel):
    """スカウト検索結果 1 件（要約 + 最新総合スコア）。"""

    id: uuid.UUID
    name: str
    position: str | None
    sport: str
    location: str | None
    height_cm: float | None
    weight_kg: float | None
    latest_total_score: float | None
    is_reference_score: bool = True  # スコアは常に参考値


class ScoreSnapshot(BaseModel):
    """分析スコアのスナップショット（レーダー・履歴用）。"""

    sprint_score: float
    ball_control_score: float
    positioning_score: float
    body_usage_score: float
    total_score: float
    analyzed_at: datetime


class MetricBenchmark(BaseModel):
    """項目別のベンチマーク（同ポジション平均）。"""

    sprint_score: float
    ball_control_score: float
    positioning_score: float
    body_usage_score: float
    total_score: float
    sample_size: int  # 比較対象人数


class AthleteScoresResponse(BaseModel):
    """選手のスコア詳細（最新 + 履歴 + アナリティクス）。"""

    id: uuid.UUID
    name: str
    position: str | None
    sport: str
    location: str | None
    height_cm: float | None
    weight_kg: float | None
    latest: ScoreSnapshot | None
    history: list[ScoreSnapshot]
    # ── アナリティクス ──
    benchmark: MetricBenchmark | None  # 同ポジション平均
    percentile: float | None  # 総合スコアの同ポジション内パーセンタイル(0-100)
    consistency: float | None  # 総合スコアの安定性(0-100, 高いほど安定)
    bmi: float | None
    is_reference_score: bool = True
