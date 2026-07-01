"""スキーマパッケージ。"""

from app.schemas.athlete import (
    AthleteProfileCreate,
    AthleteProfileResponse,
    AthleteProfileSummary,
    AthleteProfileUpdate,
)
from app.schemas.user import UserCreate, UserResponse
from app.schemas.video import (
    AnalysisResultResponse,
    AnalysisScoreSchema,
    VideoResponse,
    VideoUploadResponse,
)

__all__ = [
    "UserCreate",
    "UserResponse",
    "AthleteProfileCreate",
    "AthleteProfileUpdate",
    "AthleteProfileResponse",
    "AthleteProfileSummary",
    "VideoUploadResponse",
    "VideoResponse",
    "AnalysisScoreSchema",
    "AnalysisResultResponse",
]
