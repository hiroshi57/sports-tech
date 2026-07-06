"""活動記録（練習ログ）API の統合テスト。"""

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
from app.models import AthleteProfile, Base, User, UserRole

_TEST_DB_URL = "sqlite:///./test_activities.db"
_TEST_DB_FILE = "test_activities.db"


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
    """(profile_id, token) を返す。"""
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
        profile = AthleteProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            name="テスト選手",
            sport="football",
        )
        db.add(profile)
        db.commit()
        return profile.id, create_access_token(subject=str(user.id), role="athlete")
    finally:
        db.close()


def _scout_token(sf) -> str:
    db = sf()
    try:
        user = User(
            id=uuid.uuid4(),
            email=f"s-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.SCOUT,
            is_active=True,
        )
        db.add(user)
        db.commit()
        return create_access_token(subject=str(user.id), role="scout")
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _valid_payload(**overrides) -> dict:
    payload = {
        "activity_date": "2026-07-01",
        "activity_type": "practice",
        "duration_min": 90,
        "fatigue_level": 3,
        "notes": "シュート練習",
    }
    payload.update(overrides)
    return payload


class TestCreate:
    def test_athlete_can_create(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        res = client.post("/api/activities", json=_valid_payload(), headers=_auth(token))
        assert res.status_code == 201
        data = res.json()
        assert data["activity_type"] == "practice"
        assert data["fatigue_level"] == 3

    def test_scout_cannot_create(self, client, sf) -> None:
        token = _scout_token(sf)
        res = client.post("/api/activities", json=_valid_payload(), headers=_auth(token))
        assert res.status_code == 403

    def test_unauthenticated_returns_403(self, client) -> None:
        res = client.post("/api/activities", json=_valid_payload())
        assert res.status_code == 403

    def test_invalid_fatigue_level_returns_422(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        res = client.post(
            "/api/activities", json=_valid_payload(fatigue_level=9), headers=_auth(token)
        )
        assert res.status_code == 422

    def test_athlete_without_profile_returns_404(self, client, sf) -> None:
        db = sf()
        try:
            user = User(
                id=uuid.uuid4(),
                email=f"np-{uuid.uuid4().hex[:8]}@example.com",
                role=UserRole.ATHLETE,
                is_active=True,
            )
            db.add(user)
            db.commit()
            token = create_access_token(subject=str(user.id), role="athlete")
        finally:
            db.close()
        res = client.post("/api/activities", json=_valid_payload(), headers=_auth(token))
        assert res.status_code == 404


class TestListAndGet:
    def test_list_returns_own_only(self, client, sf) -> None:
        _, token_a = _make_athlete(sf)
        _, token_b = _make_athlete(sf)
        client.post("/api/activities", json=_valid_payload(notes="Aの記録"), headers=_auth(token_a))

        res = client.get("/api/activities", headers=_auth(token_b))
        assert res.status_code == 200
        assert all(x["notes"] != "Aの記録" for x in res.json())

    def test_date_range_filter(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        client.post(
            "/api/activities", json=_valid_payload(activity_date="2026-01-01"), headers=_auth(token)
        )
        client.post(
            "/api/activities", json=_valid_payload(activity_date="2026-12-31"), headers=_auth(token)
        )
        res = client.get(
            "/api/activities?date_from=2026-06-01&date_to=2026-12-31", headers=_auth(token)
        )
        dates = [x["activity_date"] for x in res.json()]
        assert "2026-12-31" in dates
        assert "2026-01-01" not in dates

    def test_get_other_users_activity_returns_403(self, client, sf) -> None:
        _, token_a = _make_athlete(sf)
        _, token_b = _make_athlete(sf)
        created = client.post(
            "/api/activities", json=_valid_payload(), headers=_auth(token_a)
        ).json()
        res = client.get(f"/api/activities/{created['id']}", headers=_auth(token_b))
        assert res.status_code == 403

    def test_get_nonexistent_returns_404(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        res = client.get(f"/api/activities/{uuid.uuid4()}", headers=_auth(token))
        assert res.status_code == 404


class TestUpdateDelete:
    def test_update_activity(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        created = client.post("/api/activities", json=_valid_payload(), headers=_auth(token)).json()
        res = client.patch(
            f"/api/activities/{created['id']}",
            json={"fatigue_level": 5, "notes": "更新後"},
            headers=_auth(token),
        )
        assert res.status_code == 200
        assert res.json()["fatigue_level"] == 5
        assert res.json()["notes"] == "更新後"

    def test_delete_activity(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        created = client.post("/api/activities", json=_valid_payload(), headers=_auth(token)).json()
        res = client.delete(f"/api/activities/{created['id']}", headers=_auth(token))
        assert res.status_code == 204
        res2 = client.get(f"/api/activities/{created['id']}", headers=_auth(token))
        assert res2.status_code == 404


class TestSummary:
    def test_summary_aggregates(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        client.post(
            "/api/activities",
            json=_valid_payload(activity_type="practice", duration_min=60, fatigue_level=2),
            headers=_auth(token),
        )
        client.post(
            "/api/activities",
            json=_valid_payload(activity_type="match", duration_min=90, fatigue_level=4),
            headers=_auth(token),
        )
        res = client.get("/api/activities/summary", headers=_auth(token))
        assert res.status_code == 200
        data = res.json()
        assert data["total_count"] == 2
        assert data["total_duration_min"] == 150
        assert data["avg_fatigue_level"] == 3.0
        assert data["practice_count"] == 1
        assert data["match_count"] == 1
