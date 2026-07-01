"""モデルパッケージ — 全モデルをここから import する。"""

from app.models.activity import ActivityLog, ActivityType, SelfCareRecord
from app.models.athlete import AthleteProfile
from app.models.base import Base
from app.models.training import TrainingMenu
from app.models.user import User, UserRole
from app.models.video import AnalysisResult, Video, VideoStatus

__all__ = [
    "Base",
    "User",
    "UserRole",
    "AthleteProfile",
    "Video",
    "VideoStatus",
    "AnalysisResult",
    "ActivityLog",
    "ActivityType",
    "SelfCareRecord",
    "TrainingMenu",
]
