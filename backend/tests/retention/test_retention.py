"""動画保存期間の予告・削除ロジックのテスト(D#35)。"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import AthleteProfile, Base, User, UserRole, Video, VideoStatus
from app.services import retention_service


@pytest.fixture()
def sf():
    url = "sqlite:///./test_retention.db"
    eng = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield sessionmaker(autocommit=False, autoflush=False, bind=eng)
    Base.metadata.drop_all(eng)
    eng.dispose()
    if os.path.exists("test_retention.db"):
        os.remove("test_retention.db")


def _make_video(sf, *, age_days: int, warned: bool = False) -> uuid.UUID:
    db = sf()
    try:
        user = User(
            id=uuid.uuid4(),
            email=f"a-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.ATHLETE,
            is_active=True,
        )
        db.add(user)
        db.flush()
        profile = AthleteProfile(id=uuid.uuid4(), user_id=user.id, name="選手", sport="football")
        db.add(profile)
        db.flush()
        v = Video(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.COMPLETED,
            mime_type="video/mp4",
            last_accessed_at=datetime.now(UTC) - timedelta(days=age_days),
            retention_warned=warned,
        )
        db.add(v)
        db.commit()
        return v.id
    finally:
        db.close()


class TestRetention:
    def test_expired_video_is_deleted(self, sf) -> None:
        vid = _make_video(sf, age_days=800)  # 730日超
        with patch("app.services.retention_service.s3_client.delete_s3_object") as del_s3:
            db = sf()
            try:
                res = retention_service.process_retention(db)
            finally:
                db.close()
        assert vid in res.deleted_video_ids
        del_s3.assert_called_once()
        db = sf()
        try:
            assert db.get(Video, vid) is None
        finally:
            db.close()

    def test_near_expiry_is_warned(self, sf) -> None:
        vid = _make_video(sf, age_days=720)  # 満了10日前（<14）
        db = sf()
        try:
            res = retention_service.process_retention(db)
        finally:
            db.close()
        assert vid in res.warned_video_ids
        db = sf()
        try:
            assert db.get(Video, vid).retention_warned is True
        finally:
            db.close()

    def test_fresh_video_untouched(self, sf) -> None:
        vid = _make_video(sf, age_days=10)
        db = sf()
        try:
            res = retention_service.process_retention(db)
        finally:
            db.close()
        assert vid not in res.deleted_video_ids
        assert vid not in res.warned_video_ids

    def test_already_warned_not_rewarned(self, sf) -> None:
        vid = _make_video(sf, age_days=720, warned=True)
        db = sf()
        try:
            res = retention_service.process_retention(db)
        finally:
            db.close()
        assert vid not in res.warned_video_ids
