"""練習振り返り API の統合テスト。"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import AthleteProfile, Base, User, UserRole, Video, VideoStatus

_TEST_DB_URL = "sqlite:///./test_reviews.db"
_TEST_DB_FILE = "test_reviews.db"


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


def _make_athlete(sf) -> tuple[uuid.UUID, str]:
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
        db.commit()
        return profile.id, create_access_token(subject=str(user.id), role="athlete")
    finally:
        db.close()


def _make_video(sf, profile_id: uuid.UUID) -> uuid.UUID:
    db = sf()
    try:
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile_id,
            s3_key=f"videos/{profile_id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.COMPLETED,
            mime_type="video/mp4",
        )
        db.add(video)
        db.commit()
        return video.id
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestCreate:
    def test_create_without_video(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        res = client.post(
            "/api/reviews",
            json={"self_rating": 4, "went_well": "トラップ", "to_improve": "左足"},
            headers=_auth(token),
        )
        assert res.status_code == 201
        assert res.json()["self_rating"] == 4

    def test_create_with_own_video(self, client, sf) -> None:
        profile_id, token = _make_athlete(sf)
        video_id = _make_video(sf, profile_id)
        res = client.post(
            "/api/reviews",
            json={"video_id": str(video_id), "notes": "良い動き"},
            headers=_auth(token),
        )
        assert res.status_code == 201
        assert res.json()["video_id"] == str(video_id)

    def test_create_with_others_video_returns_403(self, client, sf) -> None:
        profile_a, _ = _make_athlete(sf)
        _, token_b = _make_athlete(sf)
        video_id = _make_video(sf, profile_a)
        res = client.post(
            "/api/reviews",
            json={"video_id": str(video_id)},
            headers=_auth(token_b),
        )
        assert res.status_code == 403

    def test_invalid_rating_returns_422(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        res = client.post("/api/reviews", json={"self_rating": 9}, headers=_auth(token))
        assert res.status_code == 422

    def test_unauthenticated_returns_403(self, client) -> None:
        assert client.post("/api/reviews", json={}).status_code == 403


class TestListUpdateDelete:
    def test_list_and_filter_by_video(self, client, sf) -> None:
        profile_id, token = _make_athlete(sf)
        video_id = _make_video(sf, profile_id)
        client.post("/api/reviews", json={"notes": "動画なし"}, headers=_auth(token))
        client.post(
            "/api/reviews",
            json={"video_id": str(video_id), "notes": "動画あり"},
            headers=_auth(token),
        )
        res = client.get(f"/api/reviews?video_id={video_id}", headers=_auth(token))
        assert res.status_code == 200
        assert all(r["video_id"] == str(video_id) for r in res.json())
        assert len(res.json()) == 1

    def test_update(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        created = client.post("/api/reviews", json={"self_rating": 2}, headers=_auth(token)).json()
        res = client.patch(
            f"/api/reviews/{created['id']}", json={"self_rating": 5}, headers=_auth(token)
        )
        assert res.status_code == 200
        assert res.json()["self_rating"] == 5

    def test_delete(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        created = client.post("/api/reviews", json={"notes": "x"}, headers=_auth(token)).json()
        assert (
            client.delete(f"/api/reviews/{created['id']}", headers=_auth(token)).status_code == 204
        )
        assert client.get(f"/api/reviews/{created['id']}", headers=_auth(token)).status_code == 404

    def test_cannot_access_others_review(self, client, sf) -> None:
        _, token_a = _make_athlete(sf)
        _, token_b = _make_athlete(sf)
        created = client.post("/api/reviews", json={"notes": "a"}, headers=_auth(token_a)).json()
        res = client.get(f"/api/reviews/{created['id']}", headers=_auth(token_b))
        assert res.status_code == 403
