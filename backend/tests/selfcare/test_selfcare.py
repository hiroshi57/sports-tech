"""セルフケア（怪我リスク）API の統合テスト。"""

from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import ActivityLog, ActivityType, AthleteProfile, Base, User, UserRole

_TEST_DB_URL = "sqlite:///./test_selfcare.db"
_TEST_DB_FILE = "test_selfcare.db"


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


def _add_activity(sf, profile_id, *, days_ago: int, duration: int, fatigue: int) -> None:
    db = sf()
    try:
        db.add(
            ActivityLog(
                id=uuid.uuid4(),
                athlete_id=profile_id,
                activity_date=date.today() - timedelta(days=days_ago),
                activity_type=ActivityType.PRACTICE,
                duration_min=duration,
                fatigue_level=fatigue,
            )
        )
        db.commit()
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestRecords:
    def test_create_record(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        res = client.post(
            "/api/selfcare/records",
            json={"record_date": "2026-07-01", "sleep_hours": 7.5, "weight_kg": 65},
            headers=_auth(token),
        )
        assert res.status_code == 201
        assert res.json()["sleep_hours"] == 7.5
        assert res.json()["injury_risk_score"] is not None

    def test_scout_cannot_create(self, client, sf) -> None:
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
            token = create_access_token(subject=str(user.id), role="scout")
        finally:
            db.close()
        res = client.post(
            "/api/selfcare/records",
            json={"record_date": "2026-07-01"},
            headers=_auth(token),
        )
        assert res.status_code == 403

    def test_list_records(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        client.post(
            "/api/selfcare/records",
            json={"record_date": "2026-07-01", "sleep_hours": 8},
            headers=_auth(token),
        )
        res = client.get("/api/selfcare/records", headers=_auth(token))
        assert res.status_code == 200
        assert len(res.json()) >= 1


class TestInjuryRisk:
    def test_low_risk_when_no_activity(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        res = client.get("/api/selfcare/injury-risk", headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["risk_level"] == "low"
        assert res.json()["is_reference_score"] is True

    def test_high_risk_on_load_spike_and_fatigue(self, client, sf) -> None:
        """慢性負荷が低い中で急に高負荷+高疲労 → 高リスク。"""
        profile_id, token = _make_athlete(sf)
        # 過去（8〜27日前）は軽い負荷
        for d in range(8, 28):
            _add_activity(sf, profile_id, days_ago=d, duration=10, fatigue=2)
        # 直近7日は高負荷・高疲労
        for d in range(0, 7):
            _add_activity(sf, profile_id, days_ago=d, duration=180, fatigue=5)

        res = client.get("/api/selfcare/injury-risk", headers=_auth(token))
        assert res.status_code == 200
        data = res.json()
        assert data["risk_level"] in ("moderate", "high")
        assert data["risk_score"] > 30
        assert data["acwr"] is not None and data["acwr"] > 1.5
        assert len(data["factors"]) >= 1

    def test_unauthenticated_returns_403(self, client) -> None:
        res = client.get("/api/selfcare/injury-risk")
        assert res.status_code == 403
