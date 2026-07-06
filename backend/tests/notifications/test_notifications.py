"""通知 API の統合テスト + 分析完了フックのテスト。"""

from __future__ import annotations

import os
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import (
    AthleteProfile,
    Base,
    NotificationType,
    User,
    UserRole,
    Video,
    VideoStatus,
)
from app.services import notification_service

_TEST_DB_URL = "sqlite:///./test_notifications.db"
_TEST_DB_FILE = "test_notifications.db"


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()
    if os.path.exists(_TEST_DB_FILE):
        os.remove(_TEST_DB_FILE)


@pytest.fixture(scope="module")
def sf(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def client(sf):
    def override_get_db():
        db = sf()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(sf, role: UserRole = UserRole.ATHLETE) -> tuple[uuid.UUID, str]:
    db = sf()
    try:
        user = User(
            id=uuid.uuid4(),
            email=f"u-{uuid.uuid4().hex[:8]}@example.com",
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        return user.id, create_access_token(subject=str(user.id), role=role.value)
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestNotificationApi:
    def test_list_empty(self, client, sf) -> None:
        _, token = _make_user(sf)
        res = client.get("/api/notifications", headers=_auth(token))
        assert res.status_code == 200
        assert res.json() == []

    def test_create_and_list(self, client, sf) -> None:
        user_id, token = _make_user(sf)
        db = sf()
        try:
            notification_service.create_notification(
                db,
                user_id=user_id,
                type=NotificationType.ANALYSIS_COMPLETED,
                title="分析完了",
            )
        finally:
            db.close()

        res = client.get("/api/notifications", headers=_auth(token))
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["title"] == "分析完了"
        assert res.json()[0]["is_read"] is False

    def test_unread_count(self, client, sf) -> None:
        user_id, token = _make_user(sf)
        db = sf()
        try:
            for _ in range(3):
                notification_service.create_notification(
                    db, user_id=user_id, type=NotificationType.SCOUT_VIEWED, title="閲覧"
                )
        finally:
            db.close()
        res = client.get("/api/notifications/unread-count", headers=_auth(token))
        assert res.json()["unread_count"] == 3

    def test_mark_read(self, client, sf) -> None:
        user_id, token = _make_user(sf)
        db = sf()
        try:
            n = notification_service.create_notification(
                db, user_id=user_id, type=NotificationType.SCOUT_VIEWED, title="閲覧"
            )
            nid = n.id
        finally:
            db.close()
        res = client.post(f"/api/notifications/{nid}/read", headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["is_read"] is True

    def test_cannot_read_others_notification(self, client, sf) -> None:
        owner_id, _ = _make_user(sf)
        _, other_token = _make_user(sf)
        db = sf()
        try:
            n = notification_service.create_notification(
                db, user_id=owner_id, type=NotificationType.SCOUT_VIEWED, title="他人宛"
            )
            nid = n.id
        finally:
            db.close()
        res = client.post(f"/api/notifications/{nid}/read", headers=_auth(other_token))
        assert res.status_code == 403

    def test_read_all(self, client, sf) -> None:
        user_id, token = _make_user(sf)
        db = sf()
        try:
            for _ in range(2):
                notification_service.create_notification(
                    db, user_id=user_id, type=NotificationType.SCOUT_VIEWED, title="x"
                )
        finally:
            db.close()
        res = client.post("/api/notifications/read-all", headers=_auth(token))
        assert res.status_code == 200
        count = client.get("/api/notifications/unread-count", headers=_auth(token))
        assert count.json()["unread_count"] == 0

    def test_unauthenticated_returns_403(self, client) -> None:
        assert client.get("/api/notifications").status_code == 403


class TestAnalysisHook:
    def test_completed_analysis_creates_notification(self, sf) -> None:
        """分析完了で該当ユーザーに通知が作られる。"""
        from app.worker.celery_app import celery_app
        from app.worker.tasks import analyze_video

        celery_app.conf.task_always_eager = True

        db = sf()
        try:
            user = User(
                id=uuid.uuid4(),
                email=f"ath-{uuid.uuid4().hex[:8]}@example.com",
                role=UserRole.ATHLETE,
                is_active=True,
            )
            db.add(user)
            db.flush()
            profile = AthleteProfile(
                id=uuid.uuid4(), user_id=user.id, name="選手", sport="football"
            )
            db.add(profile)
            db.flush()
            video = Video(
                id=uuid.uuid4(),
                athlete_id=profile.id,
                s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
                status=VideoStatus.PENDING,
                mime_type="video/mp4",
            )
            db.add(video)
            db.commit()
            user_id = user.id
            video_id = video.id
        finally:
            db.close()

        from app.services.pose_estimation import PoseEstimationError

        with (
            patch("app.worker.tasks.SessionLocal", sf),
            patch(
                "app.services.analysis_engine.extract_pose_from_s3",
                side_effect=PoseEstimationError("stub"),
            ),
        ):
            analyze_video.apply(args=[str(video_id)]).get()

        db = sf()
        try:
            notes = notification_service.list_notifications(db, user_id)
            assert any(n.type == NotificationType.ANALYSIS_COMPLETED for n in notes)
            assert any(n.resource_id == video_id for n in notes)
        finally:
            db.close()
            celery_app.conf.task_always_eager = False
