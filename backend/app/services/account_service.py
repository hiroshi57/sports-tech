"""アカウントデータのエクスポート・削除サービス(外販 D #33)。

GDPR/個人情報保護の開示請求・削除請求に対応する。
- export: 本人に紐づく全データを JSON で返す（開示）
- delete: 本人アカウントを削除（FK ondelete=CASCADE で関連データも消える）
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import ActivityLog, SelfCareRecord
from app.models.athlete import AthleteProfile
from app.models.notification import Notification
from app.models.review import PracticeReview
from app.models.user import User
from app.models.video import AnalysisResult, Video


def export_account(db: Session, user: User) -> dict[str, Any]:
    """本人に紐づく全データを辞書で返す（開示請求対応）。"""
    data: dict[str, Any] = {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "birth_date": user.birth_date.isoformat() if user.birth_date else None,
            "parental_consent": user.parental_consent,
        },
        "notifications": [
            {"id": str(n.id), "type": n.type.value, "title": n.title, "is_read": n.is_read}
            for n in db.execute(
                select(Notification).where(Notification.user_id == user.id)
            ).scalars()
        ],
    }

    profile = db.execute(
        select(AthleteProfile).where(AthleteProfile.user_id == user.id)
    ).scalar_one_or_none()
    if profile is None:
        return data

    data["athlete_profile"] = {
        "id": str(profile.id),
        "name": profile.name,
        "position": profile.position,
        "sport": profile.sport,
        "location": profile.location,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "is_public": profile.is_public,
    }

    videos = list(db.execute(select(Video).where(Video.athlete_id == profile.id)).scalars())
    data["videos"] = [
        {"id": str(v.id), "status": v.status.value, "s3_key": v.s3_key} for v in videos
    ]
    video_ids = [v.id for v in videos]
    data["analyses"] = [
        {
            "id": str(r.id),
            "video_id": str(r.video_id),
            "total_score": r.total_score,
            "confidence": r.confidence,
        }
        for r in db.execute(
            select(AnalysisResult).where(AnalysisResult.video_id.in_(video_ids or [uuid.uuid4()]))
        ).scalars()
    ]
    data["activities"] = [
        {
            "id": str(a.id),
            "date": a.activity_date.isoformat(),
            "type": a.activity_type.value,
            "duration_min": a.duration_min,
            "fatigue_level": a.fatigue_level,
        }
        for a in db.execute(
            select(ActivityLog).where(ActivityLog.athlete_id == profile.id)
        ).scalars()
    ]
    data["self_care"] = [
        {
            "id": str(s.id),
            "date": s.record_date.isoformat(),
            "sleep_hours": s.sleep_hours,
            "injury_risk_score": s.injury_risk_score,
        }
        for s in db.execute(
            select(SelfCareRecord).where(SelfCareRecord.athlete_id == profile.id)
        ).scalars()
    ]
    data["reviews"] = [
        {"id": str(r.id), "self_rating": r.self_rating, "notes": r.notes}
        for r in db.execute(
            select(PracticeReview).where(PracticeReview.athlete_id == profile.id)
        ).scalars()
    ]
    return data


def delete_account(db: Session, user: User) -> None:
    """本人アカウントを削除する（関連データは FK CASCADE で削除）。"""
    db.delete(user)
    db.commit()
