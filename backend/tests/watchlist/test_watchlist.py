"""ウォッチリスト API の統合テスト(C#22)。"""

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

_DB = "sqlite:///./test_watchlist.db"
_FILE = "test_watchlist.db"


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(_DB, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()
    if os.path.exists(_FILE):
        os.remove(_FILE)


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


def _scout(sf) -> str:
    db = sf()
    try:
        u = User(
            id=uuid.uuid4(),
            email=f"s-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.SCOUT,
            is_active=True,
        )
        db.add(u)
        db.commit()
        return create_access_token(subject=str(u.id), role="scout")
    finally:
        db.close()


def _athlete(sf, *, public: bool = True) -> uuid.UUID:
    db = sf()
    try:
        u = User(
            id=uuid.uuid4(),
            email=f"a-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.ATHLETE,
            is_active=True,
        )
        db.add(u)
        db.flush()
        p = AthleteProfile(
            id=uuid.uuid4(), user_id=u.id, name="選手", sport="football", is_public=public
        )
        db.add(p)
        db.commit()
        return p.id
    finally:
        db.close()


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


class TestWatchlist:
    def test_add_and_list(self, client, sf) -> None:
        token = _scout(sf)
        aid = _athlete(sf)
        res = client.post(
            "/api/scouts/watchlist",
            json={"athlete_id": str(aid), "note": "要チェック", "tags": "左利き,MF"},
            headers=_auth(token),
        )
        assert res.status_code == 201
        assert res.json()["note"] == "要チェック"

        lst = client.get("/api/scouts/watchlist", headers=_auth(token))
        assert lst.status_code == 200
        assert any(i["athlete_id"] == str(aid) for i in lst.json())

    def test_add_duplicate_updates(self, client, sf) -> None:
        token = _scout(sf)
        aid = _athlete(sf)
        client.post("/api/scouts/watchlist", json={"athlete_id": str(aid)}, headers=_auth(token))
        res = client.post(
            "/api/scouts/watchlist",
            json={"athlete_id": str(aid), "note": "更新メモ"},
            headers=_auth(token),
        )
        assert res.status_code == 201
        assert res.json()["note"] == "更新メモ"
        lst = client.get("/api/scouts/watchlist", headers=_auth(token))
        assert sum(1 for i in lst.json() if i["athlete_id"] == str(aid)) == 1

    def test_add_private_athlete_404(self, client, sf) -> None:
        token = _scout(sf)
        aid = _athlete(sf, public=False)
        res = client.post(
            "/api/scouts/watchlist", json={"athlete_id": str(aid)}, headers=_auth(token)
        )
        assert res.status_code == 404

    def test_update_and_remove(self, client, sf) -> None:
        token = _scout(sf)
        aid = _athlete(sf)
        created = client.post(
            "/api/scouts/watchlist", json={"athlete_id": str(aid)}, headers=_auth(token)
        ).json()
        upd = client.patch(
            f"/api/scouts/watchlist/{created['id']}",
            json={"tags": "注目株"},
            headers=_auth(token),
        )
        assert upd.status_code == 200
        assert upd.json()["tags"] == "注目株"
        rm = client.delete(f"/api/scouts/watchlist/{created['id']}", headers=_auth(token))
        assert rm.status_code == 204

    def test_other_scout_cannot_remove(self, client, sf) -> None:
        t1 = _scout(sf)
        t2 = _scout(sf)
        aid = _athlete(sf)
        created = client.post(
            "/api/scouts/watchlist", json={"athlete_id": str(aid)}, headers=_auth(t1)
        ).json()
        res = client.delete(f"/api/scouts/watchlist/{created['id']}", headers=_auth(t2))
        assert res.status_code == 403

    def test_athlete_role_forbidden(self, client, sf) -> None:
        db = sf()
        try:
            u = User(
                id=uuid.uuid4(),
                email=f"x-{uuid.uuid4().hex[:8]}@example.com",
                role=UserRole.ATHLETE,
                is_active=True,
            )
            db.add(u)
            db.commit()
            token = create_access_token(subject=str(u.id), role="athlete")
        finally:
            db.close()
        assert client.get("/api/scouts/watchlist", headers=_auth(token)).status_code == 403
