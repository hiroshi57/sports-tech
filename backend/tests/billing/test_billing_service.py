"""課金サービス・エンドポイントの統合テスト(E#37 / E#38)。"""

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
from app.models import Base, Subscription, User, UserRole
from app.services import billing_service
from app.services.billing_plans import Feature, PlanTier

_DB = "sqlite:///./test_billing.db"
_FILE = "test_billing.db"


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


def _scout(sf) -> tuple[str, uuid.UUID]:
    db = sf()
    try:
        u = User(
            id=uuid.uuid4(),
            email=f"b-{uuid.uuid4().hex[:8]}@example.com",
            role=UserRole.SCOUT,
            is_active=True,
        )
        db.add(u)
        db.commit()
        return create_access_token(subject=str(u.id), role="scout"), u.id
    finally:
        db.close()


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


class TestPlansEndpoint:
    def test_plans_public(self, client) -> None:
        res = client.get("/api/billing/plans")
        assert res.status_code == 200
        tiers = [p["tier"] for p in res.json()]
        assert tiers == ["free", "starter", "pro", "enterprise"]


class TestSubscription:
    def test_default_is_free(self, client, sf) -> None:
        token, _ = _scout(sf)
        res = client.get("/api/billing/subscription", headers=_auth(token))
        assert res.status_code == 200
        body = res.json()
        assert body["plan_tier"] == "free"
        assert body["monthly_analyses"] == 3
        assert body["analyses_remaining"] == 3

    def test_free_quota_blocks_after_limit(self, client, sf) -> None:
        token, user_id = _scout(sf)
        db = sf()
        try:
            user = db.get(User, user_id)
            # FREE は 3本まで
            for _ in range(3):
                billing_service.check_can_analyze(db, user)
                billing_service.record_analysis(db, user)
            with pytest.raises(billing_service.QuotaExceededError):
                billing_service.check_can_analyze(db, user)
        finally:
            db.close()

    def test_pro_allows_overage(self, client, sf) -> None:
        token, user_id = _scout(sf)
        db = sf()
        try:
            user = db.get(User, user_id)
            billing_service.apply_subscription_active(db, user_id, PlanTier.PRO)
            sub = db.query(Subscription).filter(Subscription.user_id == user_id).one()
            sub.analyses_used = 500  # 基本枠200を超過
            db.commit()
            # overage 可なので例外にならない
            billing_service.check_can_analyze(db, user)
        finally:
            db.close()

    def test_feature_gate(self, client, sf) -> None:
        _, user_id = _scout(sf)
        db = sf()
        try:
            user = db.get(User, user_id)
            assert billing_service.has_feature(db, user, Feature.GROWTH_PREDICTION) is False
            billing_service.apply_subscription_active(db, user_id, PlanTier.PRO)
            assert billing_service.has_feature(db, user, Feature.GROWTH_PREDICTION) is True
        finally:
            db.close()


class TestCheckoutAndInvoice:
    def test_checkout_manual_without_stripe(self, client, sf) -> None:
        token, _ = _scout(sf)
        res = client.post("/api/billing/checkout", json={"tier": "pro"}, headers=_auth(token))
        assert res.status_code == 200
        body = res.json()
        assert body["mode"] == "manual"  # STRIPE鍵未設定
        assert body["checkout_url"] is None

    def test_checkout_rejects_free(self, client, sf) -> None:
        token, _ = _scout(sf)
        res = client.post("/api/billing/checkout", json={"tier": "free"}, headers=_auth(token))
        assert res.status_code == 422

    def test_invoice_billing_pro(self, client, sf) -> None:
        token, _ = _scout(sf)
        res = client.post(
            "/api/billing/invoice",
            json={"tier": "pro", "company_name": "テストFC", "contact_email": "a@b.com"},
            headers=_auth(token),
        )
        assert res.status_code == 201
        body = res.json()
        assert body["plan_tier"] == "pro"
        assert body["billing_type"] == "invoice"
        assert body["status"] == "trialing"

    def test_invoice_rejects_starter(self, client, sf) -> None:
        token, _ = _scout(sf)
        res = client.post(
            "/api/billing/invoice",
            json={"tier": "starter", "company_name": "X", "contact_email": "a@b.com"},
            headers=_auth(token),
        )
        assert res.status_code == 422


class TestWebhook:
    def test_checkout_completed_activates(self, client, sf) -> None:
        _, user_id = _scout(sf)
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(user_id),
                    "metadata": {"user_id": str(user_id), "tier": "pro"},
                    "customer": "cus_test",
                    "subscription": "sub_test",
                }
            },
        }
        res = client.post("/api/billing/webhook", json=event)
        assert res.status_code == 200
        assert res.json()["result"] == "activated:pro"

    def test_unknown_event_ignored(self, client, sf) -> None:
        res = client.post("/api/billing/webhook", json={"type": "invoice.paid", "data": {}})
        assert res.status_code == 200
        assert res.json()["result"] == "ignored"
