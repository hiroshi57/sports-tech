"""アカウント開示(export)・削除(delete) API の統合テスト(D #33)。"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import (
    ActivityLog,
    ActivityType,
    AthleteProfile,
    Base,
    User,
    UserRole,
)

_TEST_DB_URL = "sqlite:///./test_account.db"
_TEST_DB_FILE = "test_account.db"


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


def _make_athlete_with_data(sf) -> tuple[uuid.UUID, str]:
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
        db.add(
            ActivityLog(
                id=uuid.uuid4(),
                athlete_id=profile.id,
                activity_date=__import__("datetime").date(2026, 7, 1),
                activity_type=ActivityType.PRACTICE,
                duration_min=60,
                fatigue_level=3,
            )
        )
        db.commit()
        return user.id, create_access_token(subject=str(user.id), role="athlete")
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestExport:
    def test_export_returns_own_data(self, client, sf) -> None:
        _, token = _make_athlete_with_data(sf)
        res = client.get("/api/account/export", headers=_auth(token))
        assert res.status_code == 200
        data = res.json()
        assert "user" in data
        assert data["athlete_profile"]["name"] == "選手"
        assert len(data["activities"]) == 1

    def test_export_requires_auth(self, client) -> None:
        assert client.get("/api/account/export").status_code == 403


class TestDelete:
    def test_delete_removes_user_and_cascades(self, client, sf) -> None:
        user_id, token = _make_athlete_with_data(sf)
        res = client.delete("/api/account", headers=_auth(token))
        assert res.status_code == 204

        # ユーザーが消え、関連プロフィールも連鎖削除される
        db = sf()
        try:
            assert db.get(User, user_id) is None
            prof = db.execute(
                select(AthleteProfile).where(AthleteProfile.user_id == user_id)
            ).scalar_one_or_none()
            assert prof is None
        finally:
            db.close()

    def test_delete_requires_auth(self, client) -> None:
        assert client.delete("/api/account").status_code == 403
