"""Video / AnalysisResult スキーマ。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.video import VideoStatus

# ── リクエスト ──────────────────────────────────────────────────────


class VideoUploadInitRequest(BaseModel):
    """動画アップロード開始リクエスト。"""

    filename: str | None = Field(None, max_length=255, description="元のファイル名")
    content_type: str = Field(
        "video/mp4",
        description="動画の MIME タイプ (video/mp4, video/quicktime 等)",
    )
    file_size_bytes: int | None = Field(
        None,
        gt=0,
        le=500 * 1024 * 1024,  # 500 MB
        description="ファイルサイズ（バイト）",
    )


class VideoCompleteRequest(BaseModel):
    """動画アップロード完了通知リクエスト。"""

    duration_sec: int | None = Field(None, gt=0, description="動画の長さ（秒）")


SCORE_MIN = 0.0
SCORE_MAX = 100.0


def clamp_score(v: float) -> float:
    """スコアを 0〜100 の範囲にクランプする。"""
    return max(SCORE_MIN, min(SCORE_MAX, v))


class VideoUploadResponse(BaseModel):
    """動画アップロード開始レスポンス（Presigned URL 含む）。"""

    video_id: uuid.UUID
    presigned_url: str  # PUT でこの URL に直接アップロードする
    s3_key: str
    expires_in_sec: int = 3600
    instructions: str = (
        "presigned_url に Content-Type ヘッダー付きで PUT リクエストを送信してください。"
        "アップロード完了後は POST /videos/{video_id}/complete を呼んでください。"
    )


class VideoDownloadUrlResponse(BaseModel):
    """動画再生用 Presigned URL レスポンス。"""

    video_id: uuid.UUID
    download_url: str
    expires_in_sec: int = 3600


class VideoResponse(BaseModel):
    """動画情報レスポンス。"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    s3_key: str
    original_filename: str | None
    duration_sec: int | None
    status: VideoStatus
    created_at: datetime


class AnalysisScoreSchema(BaseModel):
    """AI分析スコア（各 0〜100）。"""

    sprint_score: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX)
    ball_control_score: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX)
    positioning_score: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX)
    body_usage_score: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX)
    total_score: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX)

    # スコアのクランプ（境界値の浮動小数点誤差を吸収）
    @field_validator(
        "sprint_score",
        "ball_control_score",
        "positioning_score",
        "body_usage_score",
        "total_score",
    )
    @classmethod
    def clamp(cls, v: float) -> float:
        return clamp_score(v)


class AnalysisResultResponse(BaseModel):
    """AI分析結果レスポンス。

    Note:
        スコアはAIによる参考値です。確定的な選手評価を保証するものではありません。
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    video_id: uuid.UUID
    sprint_score: float
    ball_control_score: float
    positioning_score: float
    body_usage_score: float
    total_score: float
    confidence: float
    feedback: str | None
    analyzed_at: datetime  # created_at を alias として使用
    is_reference_score: bool = True  # 常に True: 参考スコアである旨をクライアントに通知

    # created_at → analyzed_at へのマッピング
    @classmethod
    def from_orm_with_alias(cls, obj: object) -> "AnalysisResultResponse":
        data = {
            "id": obj.id,  # type: ignore[attr-defined]
            "video_id": obj.video_id,  # type: ignore[attr-defined]
            "sprint_score": obj.sprint_score,  # type: ignore[attr-defined]
            "ball_control_score": obj.ball_control_score,  # type: ignore[attr-defined]
            "positioning_score": obj.positioning_score,  # type: ignore[attr-defined]
            "body_usage_score": obj.body_usage_score,  # type: ignore[attr-defined]
            "total_score": obj.total_score,  # type: ignore[attr-defined]
            "confidence": obj.confidence,  # type: ignore[attr-defined]
            "feedback": obj.feedback,  # type: ignore[attr-defined]
            "analyzed_at": obj.created_at,  # type: ignore[attr-defined]
        }
        return cls(**data)
