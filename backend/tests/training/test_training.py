"""練習メニュー自動生成 API の統合テスト。"""

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
from app.models import (
    AnalysisResult,
    AthleteProfile,
    Base,
    User,
    UserRole,
    Video,
    VideoStatus,
)

_TEST_DB_URL = "sqlite:///./test_training.db"
_TEST_DB_FILE = "test_training.db"


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


def _make_athlete(sf, *, scores: dict | None = None) -> tuple[uuid.UUID, str]:
    """(profile_id, token) を返す。scores があれば完了済み分析を1件作る。"""
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
        if scores is not None:
            video = Video(
                id=uuid.uuid4(),
                athlete_id=profile.id,
                s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
                status=VideoStatus.COMPLETED,
                mime_type="video/mp4",
            )
            db.add(video)
            db.flush()
            db.add(
                AnalysisResult(
                    id=uuid.uuid4(),
                    video_id=video.id,
                    sprint_score=scores["sprint"],
                    ball_control_score=scores["ball_control"],
                    positioning_score=scores["positioning"],
                    body_usage_score=scores["body_usage"],
                    total_score=sum(scores.values()) / 4,
                    confidence=0.5,
                )
            )
        db.commit()
        return profile.id, create_access_token(subject=str(user.id), role="athlete")
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestGenerate:
    def test_generate_without_analysis_returns_basic(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        res = client.post(
            "/api/training/generate", json={"target_duration_min": 60}, headers=_auth(token)
        )
        assert res.status_code == 201
        data = res.json()
        assert data["is_ai_generated"] is True
        assert len(data["exercises"]) >= 1
        assert data["total_duration_min"] <= 60

    def test_generate_prioritizes_weakest_skill(self, client, sf) -> None:
        """最弱スキルのドリルが必ず含まれる。"""
        _, token = _make_athlete(
            sf,
            scores={"sprint": 90, "ball_control": 30, "positioning": 85, "body_usage": 80},
        )
        res = client.post(
            "/api/training/generate", json={"target_duration_min": 60}, headers=_auth(token)
        )
        assert res.status_code == 201
        skills = {e["target_skill"] for e in res.json()["exercises"]}
        assert "ball_control" in skills

    def test_generate_respects_duration(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        res = client.post(
            "/api/training/generate", json={"target_duration_min": 20}, headers=_auth(token)
        )
        assert res.json()["total_duration_min"] <= 20

    def test_scout_cannot_generate(self, client, sf) -> None:
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
        res = client.post("/api/training/generate", json={}, headers=_auth(token))
        assert res.status_code == 403


class TestListAndDelete:
    def test_list_and_get(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        created = client.post("/api/training/generate", json={}, headers=_auth(token)).json()
        lst = client.get("/api/training", headers=_auth(token))
        assert lst.status_code == 200
        assert any(m["id"] == created["id"] for m in lst.json())
        detail = client.get(f"/api/training/{created['id']}", headers=_auth(token))
        assert detail.status_code == 200

    def test_delete(self, client, sf) -> None:
        _, token = _make_athlete(sf)
        created = client.post("/api/training/generate", json={}, headers=_auth(token)).json()
        res = client.delete(f"/api/training/{created['id']}", headers=_auth(token))
        assert res.status_code == 204
        assert client.get(f"/api/training/{created['id']}", headers=_auth(token)).status_code == 404

    def test_cannot_access_others_menu(self, client, sf) -> None:
        _, token_a = _make_athlete(sf)
        _, token_b = _make_athlete(sf)
        created = client.post("/api/training/generate", json={}, headers=_auth(token_a)).json()
        res = client.get(f"/api/training/{created['id']}", headers=_auth(token_b))
        assert res.status_code == 403
