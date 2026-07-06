"""スカウト選手検索 API の統合テスト。"""

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
from app.models import (
    AnalysisResult,
    AthleteProfile,
    Base,
    User,
    UserRole,
    Video,
    VideoStatus,
)

_TEST_DB_URL = "sqlite:///./test_scouts.db"
_TEST_DB_FILE = "test_scouts.db"


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


def _scout_token(sf) -> str:
    db = sf()
    try:
        user = User(
            id=uuid.uuid4(),
            email=f"scout-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.SCOUT,
            is_active=True,
        )
        db.add(user)
        db.commit()
        return create_access_token(subject=str(user.id), role="scout")
    finally:
        db.close()


def _athlete_token(sf) -> str:
    db = sf()
    try:
        user = User(
            id=uuid.uuid4(),
            email=f"ath-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.ATHLETE,
            is_active=True,
        )
        db.add(user)
        db.commit()
        return create_access_token(subject=str(user.id), role="athlete")
    finally:
        db.close()


def _make_athlete(
    sf,
    *,
    name: str,
    position: str = "FW",
    sport: str = "football",
    location: str = "東京",
    is_public: bool = True,
    birth_date: date | None = None,
    parental_consent: bool = False,
    total_score: float | None = None,
) -> uuid.UUID:
    db = sf()
    try:
        user = User(
            id=uuid.uuid4(),
            email=f"a-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.ATHLETE,
            is_active=True,
            birth_date=birth_date,
            parental_consent=parental_consent,
        )
        db.add(user)
        db.flush()
        profile = AthleteProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            name=name,
            position=position,
            sport=sport,
            location=location,
            is_public=is_public,
        )
        db.add(profile)
        db.flush()

        if total_score is not None:
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
                    sprint_score=total_score,
                    ball_control_score=total_score,
                    positioning_score=total_score,
                    body_usage_score=total_score,
                    total_score=total_score,
                    confidence=0.5,
                )
            )
        db.commit()
        return profile.id
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestAuthorization:
    def test_athlete_cannot_search(self, client, sf) -> None:
        """選手ロールは検索できない（403）。"""
        token = _athlete_token(sf)
        res = client.get("/api/scouts/athletes", headers=_auth(token))
        assert res.status_code == 403

    def test_unauthenticated_returns_403(self, client) -> None:
        res = client.get("/api/scouts/athletes")
        assert res.status_code == 403


class TestSearch:
    def test_returns_only_public_athletes(self, client, sf) -> None:
        """非公開選手は検索結果に含まれない。"""
        _make_athlete(sf, name="公開太郎", is_public=True)
        _make_athlete(sf, name="非公開次郎", is_public=False)
        token = _scout_token(sf)

        res = client.get("/api/scouts/athletes?limit=100", headers=_auth(token))
        assert res.status_code == 200
        names = [a["name"] for a in res.json()]
        assert "公開太郎" in names
        assert "非公開次郎" not in names

    def test_filter_by_position(self, client, sf) -> None:
        _make_athlete(sf, name="FW選手", position="FW")
        _make_athlete(sf, name="GK選手", position="GK")
        token = _scout_token(sf)

        res = client.get("/api/scouts/athletes?position=GK&limit=100", headers=_auth(token))
        assert res.status_code == 200
        names = [a["name"] for a in res.json()]
        assert "GK選手" in names
        assert "FW選手" not in names

    def test_filter_by_min_score(self, client, sf) -> None:
        _make_athlete(sf, name="高得点", total_score=90.0)
        _make_athlete(sf, name="低得点", total_score=40.0)
        token = _scout_token(sf)

        res = client.get("/api/scouts/athletes?min_total_score=80&limit=100", headers=_auth(token))
        assert res.status_code == 200
        names = [a["name"] for a in res.json()]
        assert "高得点" in names
        assert "低得点" not in names

    def test_result_includes_reference_score_flag(self, client, sf) -> None:
        _make_athlete(sf, name="スコア付き", total_score=75.0)
        token = _scout_token(sf)
        res = client.get("/api/scouts/athletes?limit=100", headers=_auth(token))
        item = next(a for a in res.json() if a["name"] == "スコア付き")
        assert item["is_reference_score"] is True
        assert item["latest_total_score"] == 75.0

    def test_minor_without_consent_excluded(self, client, sf) -> None:
        """保護者同意のない未成年は公開されない。"""
        minor_birth = date.today() - timedelta(days=365 * 15)  # 15歳
        _make_athlete(
            sf,
            name="未成年同意なし",
            birth_date=minor_birth,
            parental_consent=False,
        )
        _make_athlete(
            sf,
            name="未成年同意あり",
            birth_date=minor_birth,
            parental_consent=True,
        )
        token = _scout_token(sf)

        res = client.get("/api/scouts/athletes?limit=100", headers=_auth(token))
        names = [a["name"] for a in res.json()]
        assert "未成年同意なし" not in names
        assert "未成年同意あり" in names


class TestDetail:
    def test_get_public_athlete_detail(self, client, sf) -> None:
        aid = _make_athlete(sf, name="詳細太郎", total_score=60.0)
        token = _scout_token(sf)
        res = client.get(f"/api/scouts/athletes/{aid}", headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["name"] == "詳細太郎"

    def test_private_athlete_detail_returns_404(self, client, sf) -> None:
        aid = _make_athlete(sf, name="非公開詳細", is_public=False)
        token = _scout_token(sf)
        res = client.get(f"/api/scouts/athletes/{aid}", headers=_auth(token))
        assert res.status_code == 404

    def test_nonexistent_athlete_returns_404(self, client, sf) -> None:
        token = _scout_token(sf)
        res = client.get(f"/api/scouts/athletes/{uuid.uuid4()}", headers=_auth(token))
        assert res.status_code == 404
