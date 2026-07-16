"""バイアス監査(A#5)・補正ループ(A#9) の統合テスト。"""

from __future__ import annotations

import os
import uuid
from datetime import date

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

_DB = "sqlite:///./test_quality.db"
_FILE = "test_quality.db"


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


def _user(sf, role: UserRole) -> tuple[str, uuid.UUID]:
    db = sf()
    try:
        u = User(
            id=uuid.uuid4(),
            email=f"q-{uuid.uuid4().hex[:8]}@example.com",
            role=role,
            is_active=True,
        )
        db.add(u)
        db.commit()
        return create_access_token(subject=str(u.id), role=role.value), u.id
    finally:
        db.close()


def _athlete_result(sf, *, total: float, birth: date, height: float, weight: float) -> uuid.UUID:
    db = sf()
    try:
        u = User(
            id=uuid.uuid4(),
            email=f"a-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.ATHLETE,
            is_active=True,
            birth_date=birth,
        )
        db.add(u)
        db.flush()
        p = AthleteProfile(
            id=uuid.uuid4(),
            user_id=u.id,
            name="選手",
            sport="football",
            position="FW",
            is_public=True,
            height_cm=height,
            weight_kg=weight,
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
        r = AnalysisResult(
            id=uuid.uuid4(),
            video_id=v.id,
            sprint_score=total,
            ball_control_score=total,
            positioning_score=total,
            body_usage_score=total,
            total_score=total,
            confidence=0.7,
        )
        db.add(r)
        db.commit()
        return r.id
    finally:
        db.close()


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


class TestProReferenceEndpoint:
    def test_public_profiles(self, client) -> None:
        res = client.get("/api/quality/pro-reference")
        assert res.status_code == 200
        positions = {p["position"] for p in res.json()}
        assert positions == {"FW", "MF", "DF", "GK"}


class TestBiasAudit:
    def test_audit_segments(self, client, sf) -> None:
        token, _ = _user(sf, UserRole.SCOUT)
        # 若年(U15)を低め、成人(24+)を高めにして乖離を作る
        for _ in range(6):
            _athlete_result(sf, total=60, birth=date(2012, 1, 1), height=160, weight=50)
        for _ in range(6):
            _athlete_result(sf, total=85, birth=date(1998, 1, 1), height=180, weight=78)

        res = client.get("/api/quality/bias-audit", headers=_auth(token))
        assert res.status_code == 200
        body = res.json()
        assert body["overall_sample"] >= 12
        segs = {s["segment"] for s in body["by_age"]}
        assert "U15" in segs and "24+" in segs

    def test_bias_audit_requires_scout(self, client, sf) -> None:
        token, _ = _user(sf, UserRole.ATHLETE)
        res = client.get("/api/quality/bias-audit", headers=_auth(token))
        assert res.status_code == 403


class TestCorrectionLoop:
    def test_submit_and_approve_applies(self, client, sf) -> None:
        reporter_token, _ = _user(sf, UserRole.ATHLETE)
        reviewer_token, _ = _user(sf, UserRole.COACH)
        rid = _athlete_result(sf, total=40, birth=date(2010, 1, 1), height=165, weight=55)

        # 申告
        res = client.post(
            "/api/quality/corrections",
            json={
                "analysis_result_id": str(rid),
                "metric": "sprint_score",
                "reason": "実際はもっと速い",
                "suggested_value": 75,
            },
            headers=_auth(reporter_token),
        )
        assert res.status_code == 201
        cid = res.json()["id"]

        # 承認 → AnalysisResult に反映
        rev = client.post(
            f"/api/quality/corrections/{cid}/review",
            json={"approve": True},
            headers=_auth(reviewer_token),
        )
        assert rev.status_code == 200
        assert rev.json()["status"] == "approved"
        assert rev.json()["resolved_value"] == 75

        # 実データに反映されているか
        db = sf()
        try:
            r = db.get(AnalysisResult, uuid.UUID(rid) if isinstance(rid, str) else rid)
            assert r.sprint_score == 75
        finally:
            db.close()

    def test_invalid_metric_rejected(self, client, sf) -> None:
        token, _ = _user(sf, UserRole.ATHLETE)
        rid = _athlete_result(sf, total=50, birth=date(2010, 1, 1), height=165, weight=55)
        res = client.post(
            "/api/quality/corrections",
            json={"analysis_result_id": str(rid), "metric": "bogus", "reason": "x"},
            headers=_auth(token),
        )
        assert res.status_code == 422

    def test_athlete_cannot_review(self, client, sf) -> None:
        reporter_token, _ = _user(sf, UserRole.ATHLETE)
        rid = _athlete_result(sf, total=50, birth=date(2010, 1, 1), height=165, weight=55)
        c = client.post(
            "/api/quality/corrections",
            json={
                "analysis_result_id": str(rid),
                "metric": "total_score",
                "reason": "y",
                "suggested_value": 60,
            },
            headers=_auth(reporter_token),
        ).json()
        res = client.post(
            f"/api/quality/corrections/{c['id']}/review",
            json={"approve": True},
            headers=_auth(reporter_token),
        )
        assert res.status_code == 403

    def test_reject_keeps_score(self, client, sf) -> None:
        reporter_token, _ = _user(sf, UserRole.ATHLETE)
        reviewer_token, _ = _user(sf, UserRole.SCOUT)
        rid = _athlete_result(sf, total=45, birth=date(2010, 1, 1), height=165, weight=55)
        c = client.post(
            "/api/quality/corrections",
            json={
                "analysis_result_id": str(rid),
                "metric": "total_score",
                "reason": "z",
                "suggested_value": 90,
            },
            headers=_auth(reporter_token),
        ).json()
        rev = client.post(
            f"/api/quality/corrections/{c['id']}/review",
            json={"approve": False, "reviewer_note": "妥当"},
            headers=_auth(reviewer_token),
        )
        assert rev.status_code == 200
        assert rev.json()["status"] == "rejected"
        db = sf()
        try:
            r = db.get(AnalysisResult, uuid.UUID(rid) if isinstance(rid, str) else rid)
            assert r.total_score == 45  # 変わらない
        finally:
            db.close()
