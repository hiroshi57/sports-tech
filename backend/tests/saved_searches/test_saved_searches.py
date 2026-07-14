"""保存検索・新着アラート API の統合テスト(C#23)。"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import (
    AnalysisResult,
    AthleteProfile,
    Base,
    User,
    UserRole,
    Video,
    VideoStatus,
)

_DB = "sqlite:///./test_saved.db"
_FILE = "test_saved.db"


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


def _athlete_with_score(sf, *, position: str, total: float, analyzed_days_ago: int) -> None:
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
            id=uuid.uuid4(),
            user_id=u.id,
            name="選手",
            sport="football",
            position=position,
            is_public=True,
        )
        db.add(p)
        db.flush()
        v = Video(
            id=uuid.uuid4(),
            athlete_id=p.id,
            s3_key=f"videos/{p.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.COMPLETED,
            mime_type="video/mp4",
        )
        db.add(v)
        db.flush()
        db.add(
            AnalysisResult(
                id=uuid.uuid4(),
                video_id=v.id,
                sprint_score=total,
                ball_control_score=total,
                positioning_score=total,
                body_usage_score=total,
                total_score=total,
                confidence=0.5,
                created_at=datetime.now(UTC) - timedelta(days=analyzed_days_ago),
            )
        )
        db.commit()
    finally:
        db.close()


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


class TestSavedSearch:
    def test_create_and_list(self, client, sf) -> None:
        token = _scout(sf)
        res = client.post(
            "/api/scouts/saved-searches",
            json={"name": "大阪のFW", "position": "FW", "min_total_score": 70},
            headers=_auth(token),
        )
        assert res.status_code == 201
        assert res.json()["name"] == "大阪のFW"

        lst = client.get("/api/scouts/saved-searches", headers=_auth(token))
        assert lst.status_code == 200
        assert any(s["name"] == "大阪のFW" for s in lst.json())

    def test_new_count_counts_recent(self, client, sf) -> None:
        token = _scout(sf)
        # 保存（last_checked_at = now）
        created = client.post(
            "/api/scouts/saved-searches",
            json={"name": "GK", "position": "GK"},
            headers=_auth(token),
        ).json()
        # 保存後に分析が付いた新着GK
        _athlete_with_score(sf, position="GK", total=80, analyzed_days_ago=-1)  # 未来=直近

        lst = client.get("/api/scouts/saved-searches", headers=_auth(token))
        gk = next(s for s in lst.json() if s["id"] == created["id"])
        assert gk["new_count"] >= 1

    def test_check_resets_new_count(self, client, sf) -> None:
        token = _scout(sf)
        _athlete_with_score(sf, position="DF", total=75, analyzed_days_ago=1)
        created = client.post(
            "/api/scouts/saved-searches",
            json={"name": "DF", "position": "DF"},
            headers=_auth(token),
        ).json()
        # 作成直後は last_checked_at=now なので過去分析は新着に含まれない
        lst = client.get("/api/scouts/saved-searches", headers=_auth(token))
        df = next(s for s in lst.json() if s["id"] == created["id"])
        assert df["new_count"] == 0

    def test_delete(self, client, sf) -> None:
        token = _scout(sf)
        created = client.post(
            "/api/scouts/saved-searches", json={"name": "x"}, headers=_auth(token)
        ).json()
        res = client.delete(f"/api/scouts/saved-searches/{created['id']}", headers=_auth(token))
        assert res.status_code == 204

    def test_other_scout_cannot_delete(self, client, sf) -> None:
        t1 = _scout(sf)
        t2 = _scout(sf)
        created = client.post(
            "/api/scouts/saved-searches", json={"name": "y"}, headers=_auth(t1)
        ).json()
        res = client.delete(f"/api/scouts/saved-searches/{created['id']}", headers=_auth(t2))
        assert res.status_code == 403

    def test_athlete_forbidden(self, client, sf) -> None:
        db = sf()
        try:
            u = User(
                id=uuid.uuid4(),
                email=f"z-{uuid.uuid4().hex[:8]}@example.com",
                role=UserRole.ATHLETE,
                is_active=True,
            )
            db.add(u)
            db.commit()
            token = create_access_token(subject=str(u.id), role="athlete")
        finally:
            db.close()
        assert client.get("/api/scouts/saved-searches", headers=_auth(token)).status_code == 403
