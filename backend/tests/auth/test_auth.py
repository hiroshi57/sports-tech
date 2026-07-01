"""認証エンドポイントの統合テスト（SQLite in-memory）。

DB 接続を SQLite で上書きし、FastAPI TestClient で E2E をテストする。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token
from app.main import app
from app.models import Base, User

# ── SQLite in-memory セットアップ ──────────────────────────────────


_TEST_DB_URL = "sqlite:///./test_auth.db"


@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()
    # テスト DB ファイルを削除
    import os

    if os.path.exists("test_auth.db"):
        os.remove("test_auth.db")


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module")
def client(test_engine, test_session_factory):
    """DB を SQLite にオーバーライドした TestClient。"""

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


# ── helpers ────────────────────────────────────────────────────────


def _register(client: TestClient, email: str, role: str = "athlete") -> dict:
    return client.post(
        "/api/auth/register",
        json={"email": email, "role": role},
    ).json()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── JWT ユニットテスト ──────────────────────────────────────────────


class TestJWT:
    def test_create_and_decode(self) -> None:
        """トークンを生成してデコードできる。"""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="athlete")
        payload = decode_access_token(token)

        assert payload["sub"] == user_id
        assert payload["role"] == "athlete"
        assert payload["type"] == "access"

    def test_invalid_token_raises(self) -> None:
        """不正なトークンは JWTError を発生させる。"""
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_access_token("invalid.token.here")

    def test_tampered_token_raises(self) -> None:
        """署名が改ざんされたトークンは JWTError を発生させる。"""
        from jose import JWTError

        token = create_access_token(subject=str(uuid.uuid4()), role="athlete")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_access_token(tampered)


# ── 登録エンドポイント ─────────────────────────────────────────────


class TestRegister:
    def test_register_athlete(self, client: TestClient) -> None:
        """選手ユーザーの登録が成功する。"""
        res = client.post(
            "/api/auth/register",
            json={"email": "athlete1@example.com", "role": "athlete"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert data["expires_in"] > 0

    def test_register_scout(self, client: TestClient) -> None:
        """スカウトユーザーの登録が成功する。"""
        res = client.post(
            "/api/auth/register",
            json={"email": "scout1@example.com", "role": "scout"},
        )
        assert res.status_code == 201

    def test_duplicate_email_returns_409(self, client: TestClient) -> None:
        """同じメールアドレスは 409 Conflict になる。"""
        email = "duplicate@example.com"
        client.post("/api/auth/register", json={"email": email})
        res = client.post("/api/auth/register", json={"email": email})
        assert res.status_code == 409

    def test_invalid_email_returns_422(self, client: TestClient) -> None:
        """不正なメールアドレスは 422 になる。"""
        res = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "role": "athlete"},
        )
        assert res.status_code == 422

    def test_minor_without_consent_returns_422(self, client: TestClient) -> None:
        """18歳未満で parental_consent=false は 422 になる。"""
        res = client.post(
            "/api/auth/register",
            json={
                "email": "minor@example.com",
                "birth_date": "2015-01-01",
                "parental_consent": False,
            },
        )
        assert res.status_code == 422

    def test_minor_with_consent_succeeds(self, client: TestClient) -> None:
        """18歳未満で parental_consent=true は登録成功する。"""
        res = client.post(
            "/api/auth/register",
            json={
                "email": "minor-ok@example.com",
                "birth_date": "2015-01-01",
                "parental_consent": True,
            },
        )
        assert res.status_code == 201

    def test_adult_without_consent_succeeds(self, client: TestClient) -> None:
        """成人は parental_consent=false でも登録成功する。"""
        res = client.post(
            "/api/auth/register",
            json={
                "email": "adult@example.com",
                "birth_date": "1995-01-01",
                "parental_consent": False,
            },
        )
        assert res.status_code == 201


# ── ログインエンドポイント ─────────────────────────────────────────


class TestLogin:
    def test_login_registered_user(self, client: TestClient) -> None:
        """登録済みユーザーがログインできる。"""
        email = "login-test@example.com"
        client.post("/api/auth/register", json={"email": email})

        res = client.post("/api/auth/login", json={"email": email})
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_login_unknown_email_returns_401(self, client: TestClient) -> None:
        """未登録メールアドレスは 401 になる。"""
        res = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com"},
        )
        assert res.status_code == 401

    def test_login_deactivated_user_returns_401(
        self, client: TestClient, test_session_factory
    ) -> None:
        """無効化されたユーザーは 401 になる。"""
        email = "deactivated@example.com"
        client.post("/api/auth/register", json={"email": email})

        # DB で直接 is_active=False に設定
        db = test_session_factory()
        from sqlalchemy import select

        user = db.execute(select(User).where(User.email == email)).scalar_one()
        user.is_active = False
        db.commit()
        db.close()

        res = client.post("/api/auth/login", json={"email": email})
        assert res.status_code == 401


# ── /me エンドポイント ────────────────────────────────────────────


class TestMe:
    def test_me_with_valid_token(self, client: TestClient) -> None:
        """有効なトークンで /me が取得できる。"""
        reg = client.post(
            "/api/auth/register",
            json={"email": "me-test@example.com", "role": "athlete"},
        ).json()
        token = reg["access_token"]

        res = client.get("/api/auth/me", headers=_auth_header(token))
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "me-test@example.com"
        assert data["role"] == "athlete"
        assert data["is_active"] is True

    def test_me_without_token_returns_403(self, client: TestClient) -> None:
        """トークンなしの /me は 403 になる。"""
        res = client.get("/api/auth/me")
        assert res.status_code == 403

    def test_me_with_invalid_token_returns_401(self, client: TestClient) -> None:
        """不正なトークンは 401 になる（RFC 6750 準拠）。"""
        res = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token"},
        )
        assert res.status_code == 401

    def test_scout_role_reflected_in_me(self, client: TestClient) -> None:
        """スカウトロールが /me のレスポンスに反映される。"""
        reg = client.post(
            "/api/auth/register",
            json={"email": "scout-me@example.com", "role": "scout"},
        ).json()
        res = client.get("/api/auth/me", headers=_auth_header(reg["access_token"]))
        assert res.json()["role"] == "scout"


# ── /logout エンドポイント ────────────────────────────────────────


class TestLogout:
    def test_logout_returns_204(self, client: TestClient) -> None:
        """ログアウトは 204 No Content を返す。"""
        reg = client.post(
            "/api/auth/register",
            json={"email": "logout-test@example.com"},
        ).json()
        res = client.post("/api/auth/logout", headers=_auth_header(reg["access_token"]))
        assert res.status_code == 204

    def test_logout_without_token_returns_403(self, client: TestClient) -> None:
        """トークンなしのログアウトは 403 になる。"""
        res = client.post("/api/auth/logout")
        assert res.status_code == 403


# ── ロール検証 Dependency テスト ──────────────────────────────────


class TestRoleDependency:
    def test_scout_token_claims(self) -> None:
        """スカウトトークンの role クレームが正しい。"""
        token = create_access_token(subject=str(uuid.uuid4()), role="scout")
        payload = decode_access_token(token)
        assert payload["role"] == "scout"

    def test_athlete_token_claims(self) -> None:
        """選手トークンの role クレームが正しい。"""
        token = create_access_token(subject=str(uuid.uuid4()), role="athlete")
        payload = decode_access_token(token)
        assert payload["role"] == "athlete"
