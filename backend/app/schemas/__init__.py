"""スキーマパッケージ。"""

from app.schemas.athlete import (
    AthleteProfileCreate,
    AthleteProfileResponse,
    AthleteProfileSummary,
    AthleteProfileUpdate,
)
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.schemas.video import (
    AnalysisResultResponse,
    AnalysisScoreSchema,
    VideoResponse,
    VideoUploadResponse,
)

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "MeResponse",
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
