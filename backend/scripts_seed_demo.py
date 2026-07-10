"""ローカル確認用デモデータ投入スクリプト（SQLite）。

使い方:
    DATABASE_URL=sqlite:///./demo.db python scripts_seed_demo.py

スカウト demo-scout@example.com と、スコア付き公開選手を数名作成する。
"""

from __future__ import annotations

import uuid

from app.core.database import SessionLocal, engine
from app.models import (
    AnalysisResult,
    AthleteProfile,
    Base,
    User,
    UserRole,
    Video,
    VideoStatus,
)

Base.metadata.create_all(engine)

DEMO = [
    ("久保 太郎", "FW", "東京", 178, 70, [82, 74, 88, 79]),
    ("三笘 次郎", "MF", "神奈川", 170, 65, [90, 85, 80, 77]),
    ("冨安 三郎", "DF", "大阪", 188, 82, [70, 60, 85, 90]),
    ("遠藤 四郎", "MF", "福岡", 178, 72, [65, 78, 72, 68]),
    ("南野 五郎", "FW", "大阪", 174, 68, [88, 80, 76, 74]),
]


def main() -> None:
    db = SessionLocal()
    try:
        scout = db.query(User).filter(User.email == "demo-scout@example.com").one_or_none()
        if scout is None:
            scout = User(
                id=uuid.uuid4(),
                email="demo-scout@example.com",
                role=UserRole.SCOUT,
                is_active=True,
            )
            db.add(scout)

        for name, pos, loc, h, w, scores in DEMO:
            if db.query(AthleteProfile).filter(AthleteProfile.name == name).first():
                continue
            user = User(
                id=uuid.uuid4(),
                email=f"{uuid.uuid4().hex[:8]}@example.com",
                role=UserRole.ATHLETE,
                is_active=True,
            )
            db.add(user)
            db.flush()
            profile = AthleteProfile(
                id=uuid.uuid4(),
                user_id=user.id,
                name=name,
                position=pos,
                sport="football",
                location=loc,
                height_cm=h,
                weight_kg=w,
                is_public=True,
            )
            db.add(profile)
            db.flush()
            # 履歴用に3本の動画+分析
            for i, factor in enumerate([0.9, 0.95, 1.0]):
                video = Video(
                    id=uuid.uuid4(),
                    athlete_id=profile.id,
                    s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
                    status=VideoStatus.COMPLETED,
                    mime_type="video/mp4",
                )
                db.add(video)
                db.flush()
                sp, bc, po, bo = (round(s * factor, 1) for s in scores)
                total = round(sp * 0.3 + bc * 0.3 + po * 0.2 + bo * 0.2, 1)
                db.add(
                    AnalysisResult(
                        id=uuid.uuid4(),
                        video_id=video.id,
                        sprint_score=sp,
                        ball_control_score=bc,
                        positioning_score=po,
                        body_usage_score=bo,
                        total_score=total,
                        confidence=0.5,
                    )
                )
        db.commit()
        print("seeded: demo-scout@example.com / 選手", len(DEMO), "名")
    finally:
        db.close()


if __name__ == "__main__":
    main()
