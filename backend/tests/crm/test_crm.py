"""スカウトCRM(C#25-30)の統合テスト。"""

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

_DB = "sqlite:///./test_crm.db"
_FILE = "test_crm.db"


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
            email=f"c-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.SCOUT,
            is_active=True,
        )
        db.add(u)
        db.commit()
        return create_access_token(subject=str(u.id), role="scout")
    finally:
        db.close()


def _athlete(
    sf,
    *,
    total: float = 70,
    position: str = "FW",
    duration: int | None = 300,
) -> tuple[str, uuid.UUID, uuid.UUID, uuid.UUID]:
    """選手を作成し (token, profile_id, video_id, result_id) を返す。"""
    db = sf()
    try:
        u = User(
            id=uuid.uuid4(),
            email=f"a-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.ATHLETE,
            is_active=True,
            birth_date=date(2008, 4, 1),
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
            height_cm=172.0,
            weight_kg=62.0,
        )
        db.add(p)
        db.flush()
        v = Video(
            id=uuid.uuid4(),
            athlete_id=p.id,
            s3_key=f"videos/{p.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.COMPLETED,
            mime_type="video/mp4",
            duration_sec=duration,
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
        token = create_access_token(subject=str(u.id), role="athlete")
        return token, p.id, v.id, r.id
    finally:
        db.close()


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


class TestContacts:
    def test_pipeline_crud(self, client, sf) -> None:
        scout = _scout(sf)
        _, pid, _, _ = _athlete(sf)
        created = client.post(
            "/api/scouts/contacts",
            json={"athlete_profile_id": str(pid), "stage": "interested", "note": "注目"},
            headers=_auth(scout),
        )
        assert created.status_code == 201
        cid = created.json()["id"]

        # ステージ更新
        up = client.patch(
            f"/api/scouts/contacts/{cid}", json={"stage": "offer"}, headers=_auth(scout)
        )
        assert up.status_code == 200
        assert up.json()["stage"] == "offer"

        # パイプライン集計
        pipe = client.get("/api/scouts/contacts/pipeline", headers=_auth(scout)).json()
        offer = next(p for p in pipe if p["stage"] == "offer")
        assert offer["count"] >= 1

        # 削除
        assert client.delete(f"/api/scouts/contacts/{cid}", headers=_auth(scout)).status_code == 204

    def test_contact_includes_athlete_info(self, client, sf) -> None:
        scout = _scout(sf)
        _, pid, _, _ = _athlete(sf, total=82, position="MF")
        created = client.post(
            "/api/scouts/contacts",
            json={"athlete_profile_id": str(pid)},
            headers=_auth(scout),
        )
        assert created.status_code == 201
        body = created.json()
        # パイプライン表示用に選手情報が同梱される
        assert body["athlete_name"] == "選手"
        assert body["athlete_position"] == "MF"
        assert body["athlete_total_score"] == 82

    def test_other_scout_cannot_update(self, client, sf) -> None:
        s1, s2 = _scout(sf), _scout(sf)
        _, pid, _, _ = _athlete(sf)
        c = client.post(
            "/api/scouts/contacts",
            json={"athlete_profile_id": str(pid)},
            headers=_auth(s1),
        ).json()
        res = client.patch(
            f"/api/scouts/contacts/{c['id']}", json={"stage": "signed"}, headers=_auth(s2)
        )
        assert res.status_code == 403


class TestNotes:
    def test_share_and_list(self, client, sf) -> None:
        s1, s2 = _scout(sf), _scout(sf)
        _, pid, _, _ = _athlete(sf)
        client.post(
            "/api/scouts/notes",
            json={"athlete_profile_id": str(pid), "body": "左足のキック精度が高い"},
            headers=_auth(s1),
        )
        # 別のスカウトからも見える（チーム内共有）
        lst = client.get(f"/api/scouts/notes?athlete_profile_id={pid}", headers=_auth(s2))
        assert lst.status_code == 200
        assert any("左足" in n["body"] for n in lst.json())


class TestClips:
    def test_create_and_list(self, client, sf) -> None:
        scout = _scout(sf)
        _, _, vid, _ = _athlete(sf, duration=300)
        res = client.post(
            f"/api/scouts/videos/{vid}/clips",
            json={"title": "1対1突破", "start_sec": 12.5, "end_sec": 20.0},
            headers=_auth(scout),
        )
        assert res.status_code == 201
        lst = client.get(f"/api/scouts/videos/{vid}/clips", headers=_auth(scout))
        assert len(lst.json()) == 1

    def test_end_beyond_duration_rejected(self, client, sf) -> None:
        scout = _scout(sf)
        _, _, vid, _ = _athlete(sf, duration=60)
        res = client.post(
            f"/api/scouts/videos/{vid}/clips",
            json={"title": "x", "start_sec": 0, "end_sec": 120},
            headers=_auth(scout),
        )
        assert res.status_code == 422


class TestSimilarAndMarketValue:
    def test_similar_returns_sorted(self, client, sf) -> None:
        scout = _scout(sf)
        _, pid, _, _ = _athlete(sf, total=70, position="FW")
        _athlete(sf, total=71, position="FW")  # 近い
        _athlete(sf, total=40, position="DF")  # 遠い
        res = client.get(f"/api/scouts/athletes/{pid}/similar", headers=_auth(scout))
        assert res.status_code == 200
        sims = res.json()
        assert len(sims) >= 2
        assert sims[0]["similarity"] >= sims[-1]["similarity"]

    def test_market_value_range(self, client, sf) -> None:
        scout = _scout(sf)
        _, pid, _, _ = _athlete(sf, total=80, position="FW")
        res = client.get(f"/api/scouts/athletes/{pid}/market-value", headers=_auth(scout))
        assert res.status_code == 200
        body = res.json()
        assert 0 < body["low_jpy"] < body["high_jpy"]
        assert body["is_reference_score"] is True


class TestConsent:
    def test_get_and_update_consent(self, client, sf) -> None:
        atoken, _, _, _ = _athlete(sf)
        res = client.get("/api/athletes/me/consent", headers=_auth(atoken))
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body["is_minor"], bool)
        assert body["video_retention_days"] == 90

        # 同意を付与 → 取消 で往復できる
        on = client.patch(
            "/api/athletes/me/consent",
            json={"consent_granted": True},
            headers=_auth(atoken),
        )
        assert on.status_code == 200
        assert on.json()["consent_granted"] is True

        off = client.patch(
            "/api/athletes/me/consent",
            json={"consent_granted": False},
            headers=_auth(atoken),
        )
        assert off.status_code == 200
        assert off.json()["consent_granted"] is False

    def test_scout_cannot_access_consent(self, client, sf) -> None:
        scout = _scout(sf)
        res = client.get("/api/athletes/me/consent", headers=_auth(scout))
        assert res.status_code == 403


class TestProfileViews:
    def test_athlete_sees_views(self, client, sf) -> None:
        scout = _scout(sf)
        atoken, pid, _, _ = _athlete(sf)
        # スカウトがカルテを閲覧 → 記録される
        client.get(f"/api/scouts/athletes/{pid}/scores", headers=_auth(scout))
        res = client.get("/api/athletes/me/profile-views", headers=_auth(atoken))
        assert res.status_code == 200
        body = res.json()
        assert body["total_views"] >= 1
        assert body["recent"][0]["viewer_role"] in ("scout", "coach")
