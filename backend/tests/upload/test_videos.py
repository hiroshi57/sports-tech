"""動画アップロード API の統合テスト。

S3 操作は unittest.mock でパッチし、AWS 接続なしでテストする。
DB は SQLite in-memory を使用する。
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import AthleteProfile, Base, User, UserRole, Video, VideoStatus

# ── DB セットアップ ─────────────────────────────────────────────────

_TEST_DB_URL = "sqlite:///./test_videos.db"


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()
    import os

    if os.path.exists("test_videos.db"):
        os.remove("test_videos.db")


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module")
def client(test_engine, test_session_factory):
    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── テストデータ生成ヘルパー ────────────────────────────────────────


def _create_athlete_user(session_factory) -> tuple[User, AthleteProfile, str]:
    """選手ユーザー + プロフィールを作成し、JWT トークンも返す。"""
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
        db.refresh(user)
        db.refresh(profile)

        token = create_access_token(subject=str(user.id), role=user.role.value)
        return user, profile, token
    finally:
        db.close()


def _create_scout_user(session_factory) -> tuple[User, str]:
    """スカウトユーザーを作成し、JWT トークンも返す。"""
    db = session_factory()
    try:
        user = User(
            id=uuid.uuid4(),
            email=f"scout-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.SCOUT,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(subject=str(user.id), role=user.role.value)
        return user, token
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── S3 モック ────────────────────────────────────────────────────────

_MOCK_PRESIGNED_URL = "https://s3.example.com/presigned-put-url"
_MOCK_DOWNLOAD_URL = "https://s3.example.com/presigned-get-url"


def _mock_s3_upload():
    """generate_presigned_upload_url をモックするコンテキストマネージャ。"""
    return patch(
        "app.core.s3.generate_presigned_upload_url",
        return_value=_MOCK_PRESIGNED_URL,
    )


def _mock_s3_download():
    return patch(
        "app.core.s3.generate_presigned_download_url",
        return_value=_MOCK_DOWNLOAD_URL,
    )


def _mock_s3_delete():
    return patch("app.core.s3.delete_s3_object", return_value=None)


# ── POST /api/videos/upload-url ─────────────────────────────────────


class TestInitiateUpload:
    def test_athlete_gets_presigned_url(self, client: TestClient, test_session_factory) -> None:
        """選手が Presigned URL を取得できる。"""
        _, _, token = _create_athlete_user(test_session_factory)

        with _mock_s3_upload():
            res = client.post(
                "/api/videos/upload-url",
                json={"filename": "practice.mp4", "content_type": "video/mp4"},
                headers=_auth(token),
            )

        assert res.status_code == 201
        data = res.json()
        assert data["presigned_url"] == _MOCK_PRESIGNED_URL
        assert "video_id" in data
        assert data["s3_key"].startswith("videos/")
        assert ".mp4" in data["s3_key"]

    def test_scout_cannot_upload(self, client: TestClient, test_session_factory) -> None:
        """スカウトは動画をアップロードできない（403）。"""
        _, token = _create_scout_user(test_session_factory)

        with _mock_s3_upload():
            res = client.post(
                "/api/videos/upload-url",
                json={"content_type": "video/mp4"},
                headers=_auth(token),
            )
        assert res.status_code == 403

    def test_invalid_mime_type_returns_422(self, client: TestClient, test_session_factory) -> None:
        """非対応の MIME タイプは 422 になる。"""
        _, _, token = _create_athlete_user(test_session_factory)

        with _mock_s3_upload():
            res = client.post(
                "/api/videos/upload-url",
                json={"content_type": "image/png"},
                headers=_auth(token),
            )
        assert res.status_code == 422

    def test_file_too_large_returns_422(self, client: TestClient, test_session_factory) -> None:
        """500MB を超えるファイルサイズは 422 になる。"""
        _, _, token = _create_athlete_user(test_session_factory)

        with _mock_s3_upload():
            res = client.post(
                "/api/videos/upload-url",
                json={
                    "content_type": "video/mp4",
                    "file_size_bytes": 600 * 1024 * 1024,  # 600 MB
                },
                headers=_auth(token),
            )
        assert res.status_code == 422

    def test_athlete_without_profile_returns_404(
        self, client: TestClient, test_session_factory
    ) -> None:
        """プロフィール未登録の選手は 404 になる。"""
        db = test_session_factory()
        try:
            user = User(
                id=uuid.uuid4(),
                email=f"noprofile-{uuid.uuid4().hex[:8]}@example.com",
                role=UserRole.ATHLETE,
                is_active=True,
            )
            db.add(user)
            db.commit()
            token = create_access_token(subject=str(user.id), role="athlete")
        finally:
            db.close()

        with _mock_s3_upload():
            res = client.post(
                "/api/videos/upload-url",
                json={"content_type": "video/mp4"},
                headers=_auth(token),
            )
        assert res.status_code == 404

    def test_unauthenticated_returns_403(self, client: TestClient) -> None:
        """認証なしは 403 になる。"""
        res = client.post(
            "/api/videos/upload-url",
            json={"content_type": "video/mp4"},
        )
        assert res.status_code == 403

    def test_quicktime_mime_accepted(self, client: TestClient, test_session_factory) -> None:
        """video/quicktime（.mov）も受け付ける。"""
        _, _, token = _create_athlete_user(test_session_factory)

        with _mock_s3_upload():
            res = client.post(
                "/api/videos/upload-url",
                json={"filename": "clip.mov", "content_type": "video/quicktime"},
                headers=_auth(token),
            )
        assert res.status_code == 201
        assert ".mov" in res.json()["s3_key"]


# ── POST /api/videos/{id}/complete ──────────────────────────────────


class TestCompleteUpload:
    def _create_pending_video(self, session_factory, profile: AthleteProfile) -> Video:
        """PENDING 状態の Video レコードを直接作成する。"""
        db = session_factory()
        try:
            video = Video(
                id=uuid.uuid4(),
                athlete_id=profile.id,
                s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
                status=VideoStatus.PENDING,
                mime_type="video/mp4",
            )
            db.add(video)
            db.commit()
            db.refresh(video)
            return video
        finally:
            db.close()

    def test_complete_upload_success(self, client: TestClient, test_session_factory) -> None:
        """アップロード完了通知が成功する。"""
        _, profile, token = _create_athlete_user(test_session_factory)
        video = self._create_pending_video(test_session_factory, profile)

        res = client.post(
            f"/api/videos/{video.id}/complete",
            json={"duration_sec": 120},
            headers=_auth(token),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(video.id)
        assert data["duration_sec"] == 120
        assert data["status"] == "pending"

    def test_complete_nonexistent_video_returns_404(
        self, client: TestClient, test_session_factory
    ) -> None:
        """存在しない動画 ID は 404 になる。"""
        _, _, token = _create_athlete_user(test_session_factory)

        res = client.post(
            f"/api/videos/{uuid.uuid4()}/complete",
            json={},
            headers=_auth(token),
        )
        assert res.status_code == 404


# ── GET /api/videos ─────────────────────────────────────────────────


class TestListVideos:
    def test_list_own_videos(self, client: TestClient, test_session_factory) -> None:
        """自分の動画一覧が取得できる。"""
        _, profile, token = _create_athlete_user(test_session_factory)

        # 動画を2件作成
        db = test_session_factory()
        for _ in range(2):
            db.add(
                Video(
                    id=uuid.uuid4(),
                    athlete_id=profile.id,
                    s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
                    status=VideoStatus.PENDING,
                    mime_type="video/mp4",
                )
            )
        db.commit()
        db.close()

        res = client.get("/api/videos", headers=_auth(token))
        assert res.status_code == 200
        assert len(res.json()) >= 2

    def test_pagination(self, client: TestClient, test_session_factory) -> None:
        """limit / offset でページネーションできる。"""
        _, _, token = _create_athlete_user(test_session_factory)

        res = client.get("/api/videos?limit=1&offset=0", headers=_auth(token))
        assert res.status_code == 200
        assert len(res.json()) <= 1


# ── GET /api/videos/{id} ────────────────────────────────────────────


class TestGetVideo:
    def test_get_own_video(self, client: TestClient, test_session_factory) -> None:
        """自分の動画詳細を取得できる。"""
        _, profile, token = _create_athlete_user(test_session_factory)

        db = test_session_factory()
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.COMPLETED,
            mime_type="video/mp4",
        )
        db.add(video)
        db.commit()
        video_id = video.id
        db.close()

        res = client.get(f"/api/videos/{video_id}", headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["id"] == str(video_id)

    def test_get_other_users_video_returns_403(
        self, client: TestClient, test_session_factory
    ) -> None:
        """他ユーザーの動画は 403 になる。"""
        # 選手 A の動画
        _, profile_a, _ = _create_athlete_user(test_session_factory)
        db = test_session_factory()
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile_a.id,
            s3_key=f"videos/{profile_a.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.PENDING,
            mime_type="video/mp4",
        )
        db.add(video)
        db.commit()
        video_id = video.id
        db.close()

        # 選手 B のトークンでアクセス
        _, _, token_b = _create_athlete_user(test_session_factory)
        res = client.get(f"/api/videos/{video_id}", headers=_auth(token_b))
        assert res.status_code == 403


# ── GET /api/videos/{id}/download ───────────────────────────────────


class TestGetDownloadUrl:
    def test_get_download_url_for_completed_video(
        self, client: TestClient, test_session_factory
    ) -> None:
        """COMPLETED 動画の再生 URL を取得できる。"""
        _, profile, token = _create_athlete_user(test_session_factory)

        db = test_session_factory()
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.COMPLETED,
            mime_type="video/mp4",
        )
        db.add(video)
        db.commit()
        video_id = video.id
        db.close()

        with _mock_s3_download():
            res = client.get(f"/api/videos/{video_id}/download", headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["download_url"] == _MOCK_DOWNLOAD_URL

    def test_pending_video_returns_409(self, client: TestClient, test_session_factory) -> None:
        """PENDING 動画は再生 URL を取得できない（409）。"""
        _, profile, token = _create_athlete_user(test_session_factory)

        db = test_session_factory()
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.PENDING,
            mime_type="video/mp4",
        )
        db.add(video)
        db.commit()
        video_id = video.id
        db.close()

        with _mock_s3_download():
            res = client.get(f"/api/videos/{video_id}/download", headers=_auth(token))
        assert res.status_code == 409


# ── DELETE /api/videos/{id} ─────────────────────────────────────────


class TestDeleteVideo:
    def test_delete_pending_video(self, client: TestClient, test_session_factory) -> None:
        """PENDING 動画を削除できる（S3 削除もモック）。"""
        _, profile, token = _create_athlete_user(test_session_factory)

        db = test_session_factory()
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.PENDING,
            mime_type="video/mp4",
        )
        db.add(video)
        db.commit()
        video_id = video.id
        db.close()

        with _mock_s3_delete():
            res = client.delete(f"/api/videos/{video_id}", headers=_auth(token))
        assert res.status_code == 204

        # 削除後は 404 になる
        with _mock_s3_delete():
            res2 = client.get(f"/api/videos/{video_id}", headers=_auth(token))
        assert res2.status_code == 404

    def test_delete_processing_video_returns_409(
        self, client: TestClient, test_session_factory
    ) -> None:
        """PROCESSING 状態の動画は削除できない（409）。"""
        _, profile, token = _create_athlete_user(test_session_factory)

        db = test_session_factory()
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.PROCESSING,
            mime_type="video/mp4",
        )
        db.add(video)
        db.commit()
        video_id = video.id
        db.close()

        with _mock_s3_delete():
            res = client.delete(f"/api/videos/{video_id}", headers=_auth(token))
        assert res.status_code == 409

    def test_delete_other_users_video_returns_403(
        self, client: TestClient, test_session_factory
    ) -> None:
        """他ユーザーの動画は削除できない（403）。"""
        _, profile_a, _ = _create_athlete_user(test_session_factory)
        _, _, token_b = _create_athlete_user(test_session_factory)

        db = test_session_factory()
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile_a.id,
            s3_key=f"videos/{profile_a.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.PENDING,
            mime_type="video/mp4",
        )
        db.add(video)
        db.commit()
        video_id = video.id
        db.close()

        with _mock_s3_delete():
            res = client.delete(f"/api/videos/{video_id}", headers=_auth(token_b))
        assert res.status_code == 403


# ── s3.py ユニットテスト ─────────────────────────────────────────────


class TestS3Utils:
    def test_build_s3_key_mp4(self) -> None:
        """MP4 ファイルの S3 キーが正しく生成される。"""
        from app.core.s3 import build_s3_key

        athlete_id = uuid.uuid4()
        key = build_s3_key(athlete_id, "practice.mp4")
        assert key.startswith(f"videos/{athlete_id}/")
        assert key.endswith(".mp4")

    def test_build_s3_key_no_filename(self) -> None:
        """ファイル名なしの場合は .mp4 が付く。"""
        from app.core.s3 import build_s3_key

        key = build_s3_key(uuid.uuid4())
        assert key.endswith(".mp4")

    def test_build_s3_key_dangerous_extension_normalized(self) -> None:
        """危険な拡張子は .mp4 に正規化される。"""
        from app.core.s3 import build_s3_key

        key = build_s3_key(uuid.uuid4(), "evil.sh")
        assert key.endswith(".mp4")

    def test_validate_mime_type(self) -> None:
        """MIME タイプバリデーションが正しく動作する。"""
        from app.core.s3 import validate_mime_type

        assert validate_mime_type("video/mp4") is True
        assert validate_mime_type("video/quicktime") is True
        assert validate_mime_type("image/png") is False
        assert validate_mime_type("application/octet-stream") is False

    def test_validate_file_size(self) -> None:
        """ファイルサイズバリデーションが正しく動作する。"""
        from app.core.s3 import validate_file_size

        assert validate_file_size(1024) is True
        assert validate_file_size(500 * 1024 * 1024) is True  # ちょうど 500 MB
        assert validate_file_size(500 * 1024 * 1024 + 1) is False  # 超過
        assert validate_file_size(0) is False
