"""モデルパッケージ — 全モデルをここから import する。"""

from app.models.activity import ActivityLog, ActivityType, SelfCareRecord
from app.models.athlete import AthleteProfile
from app.models.base import Base
from app.models.notification import Notification, NotificationType
from app.models.review import PracticeReview
from app.models.training import TrainingMenu
from app.models.user import User, UserRole
from app.models.video import AnalysisResult, Video, VideoStatus
from app.models.watchlist import WatchlistItem

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
    "Notification",
    "NotificationType",
    "PracticeReview",
    "WatchlistItem",
]
