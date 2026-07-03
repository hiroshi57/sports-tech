"""AI 分析パイプラインの統合テスト。

- Celery は eager モード（task_always_eager=True）で同期実行する
- ワーカーの DB セッションはテスト用 SQLite に patch する
- 分析エンジンはスタブなので決定論的スコアが返る
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import AnalysisResult, AthleteProfile, Base, User, UserRole, Video, VideoStatus
from app.services import analysis_engine
from app.worker.celery_app import celery_app
from app.worker.tasks import analyze_video, dispatch_analysis

_TEST_DB_URL = "sqlite:///./test_analysis.db"
_TEST_DB_FILE = "test_analysis.db"


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()
    if os.path.exists(_TEST_DB_FILE):
        os.remove(_TEST_DB_FILE)


@pytest.fixture(scope="module")
def session_factory(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module", autouse=True)
def celery_eager():
    """Celery を同期実行モードにする。"""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False
    yield
    celery_app.conf.task_always_eager = False


@pytest.fixture(autouse=True)
def patch_worker_session(session_factory):
    """ワーカーが使う SessionLocal をテスト DB に差し替える。"""
    with patch("app.worker.tasks.SessionLocal", session_factory):
        yield


@pytest.fixture(scope="module")
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── ヘルパー ─────────────────────────────────────────────────────────


def _create_athlete(session_factory) -> tuple[uuid.UUID, uuid.UUID, str]:
    """(user_id, profile_id, token) を返す。"""
    db = session_factory()
    try:
        user = User(
            id=uuid.uuid4(),
            email=f"athlete-{uuid.uuid4().hex[:8]}@example.com",
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
            is_public=True,
        )
        db.add(profile)
        db.commit()
        token = create_access_token(subject=str(user.id), role=user.role.value)
        return user.id, profile.id, token
    finally:
        db.close()


def _create_video(
    session_factory,
    profile_id: uuid.UUID,
    status: VideoStatus = VideoStatus.PENDING,
) -> uuid.UUID:
    db = session_factory()
    try:
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile_id,
            s3_key=f"videos/{profile_id}/{uuid.uuid4().hex}.mp4",
            status=status,
            mime_type="video/mp4",
        )
        db.add(video)
        db.commit()
        return video.id
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 分析エンジン（スタブ）単体 ───────────────────────────────────────


class TestAnalysisEngine:
    def test_scores_in_valid_range(self) -> None:
        """全スコアが 0〜100 に収まる。"""
        scores = analysis_engine.analyze(uuid.uuid4(), "videos/x/y.mp4")
        for v in (
            scores.sprint_score,
            scores.ball_control_score,
            scores.positioning_score,
            scores.body_usage_score,
            scores.total_score,
        ):
            assert 0 <= v <= 100

    def test_deterministic_for_same_video(self) -> None:
        """同じ動画 ID なら同じスコアを返す（スタブの決定論性）。"""
        vid = uuid.uuid4()
        a = analysis_engine.analyze(vid, "k")
        b = analysis_engine.analyze(vid, "k")
        assert a == b

    def test_low_confidence_and_stub_feedback(self) -> None:
        """スタブは低 confidence + 開発中の注記を返す。"""
        scores = analysis_engine.analyze(uuid.uuid4(), "k")
        assert scores.confidence == analysis_engine.STUB_CONFIDENCE
        assert "プレースホルダー" in scores.feedback


# ── analyze_video タスク ─────────────────────────────────────────────


class TestAnalyzeVideoTask:
    def test_completes_video_and_saves_result(self, session_factory) -> None:
        """PENDING 動画が COMPLETED になり AnalysisResult が保存される。"""
        _, profile_id, _ = _create_athlete(session_factory)
        video_id = _create_video(session_factory, profile_id)

        result = analyze_video.apply(args=[str(video_id)]).get()
        assert result["status"] == "completed"

        db = session_factory()
        try:
            video = db.get(Video, video_id)
            assert video.status == VideoStatus.COMPLETED
            analysis = db.query(AnalysisResult).filter(AnalysisResult.video_id == video_id).one()
            assert 0 <= analysis.total_score <= 100
            assert analysis.confidence == analysis_engine.STUB_CONFIDENCE
        finally:
            db.close()

    def test_missing_video_returns_not_found(self) -> None:
        """存在しない動画 ID はスキップされる。"""
        result = analyze_video.apply(args=[str(uuid.uuid4())]).get()
        assert result["status"] == "not_found"

    def test_already_completed_video_is_skipped(self, session_factory) -> None:
        """COMPLETED 済み動画は再分析しない。"""
        _, profile_id, _ = _create_athlete(session_factory)
        video_id = _create_video(session_factory, profile_id, status=VideoStatus.COMPLETED)

        result = analyze_video.apply(args=[str(video_id)]).get()
        assert result["status"] == "completed"

        db = session_factory()
        try:
            count = db.query(AnalysisResult).filter(AnalysisResult.video_id == video_id).count()
            assert count == 0  # 分析は実行されていない
        finally:
            db.close()

    def test_engine_failure_marks_video_failed(self, session_factory) -> None:
        """分析エンジンが失敗し続けると FAILED になる。"""
        _, profile_id, _ = _create_athlete(session_factory)
        video_id = _create_video(session_factory, profile_id)

        with patch(
            "app.worker.tasks.analysis_engine.analyze",
            side_effect=RuntimeError("boom"),
        ):
            result = analyze_video.apply(args=[str(video_id)]).get()

        assert result["status"] == "failed"
        db = session_factory()
        try:
            video = db.get(Video, video_id)
            assert video.status == VideoStatus.FAILED
        finally:
            db.close()

    def test_dispatch_returns_none_on_broker_error(self) -> None:
        """broker 到達不能でも例外を投げず None を返す。"""
        with patch(
            "app.worker.tasks.analyze_video.delay",
            side_effect=ConnectionError("broker down"),
        ):
            assert dispatch_analysis(uuid.uuid4()) is None


# ── API 統合: complete → 分析 → 結果取得 ─────────────────────────────


class TestAnalysisApi:
    def test_complete_upload_triggers_analysis(self, client: TestClient, session_factory) -> None:
        """complete 通知で分析が走り、結果 API でスコアが取れる（E2E）。"""
        _, profile_id, token = _create_athlete(session_factory)
        video_id = _create_video(session_factory, profile_id)

        # eager モードなので complete のレスポンス時点で分析完了
        res = client.post(
            f"/api/videos/{video_id}/complete",
            json={"duration_sec": 60},
            headers=_auth(token),
        )
        assert res.status_code == 200

        res2 = client.get(f"/api/videos/{video_id}/analysis", headers=_auth(token))
        assert res2.status_code == 200
        data = res2.json()
        assert data["is_reference_score"] is True
        assert 0 <= data["total_score"] <= 100
        assert data["video_id"] == str(video_id)

    def test_analysis_of_pending_video_returns_409(
        self, client: TestClient, session_factory
    ) -> None:
        """未分析（PENDING）の動画の結果取得は 409。"""
        _, profile_id, token = _create_athlete(session_factory)
        video_id = _create_video(session_factory, profile_id)

        res = client.get(f"/api/videos/{video_id}/analysis", headers=_auth(token))
        assert res.status_code == 409

    def test_analysis_of_other_users_video_returns_403(
        self, client: TestClient, session_factory
    ) -> None:
        """他ユーザーの分析結果は 403。"""
        _, profile_a, _ = _create_athlete(session_factory)
        video_id = _create_video(session_factory, profile_a, status=VideoStatus.COMPLETED)
        _, _, token_b = _create_athlete(session_factory)

        res = client.get(f"/api/videos/{video_id}/analysis", headers=_auth(token_b))
        assert res.status_code == 403

    def test_completed_video_without_result_returns_404(
        self, client: TestClient, session_factory
    ) -> None:
        """COMPLETED だが結果レコードがない場合は 404。"""
        _, profile_id, token = _create_athlete(session_factory)
        video_id = _create_video(session_factory, profile_id, status=VideoStatus.COMPLETED)

        res = client.get(f"/api/videos/{video_id}/analysis", headers=_auth(token))
        assert res.status_code == 404
