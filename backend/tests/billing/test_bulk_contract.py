"""一括契約(E#40)のテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import bulk_contract
from app.services.billing_plans import PlanTier


class TestBulkQuoteService:
    def test_volume_discount_tiers(self) -> None:
        assert bulk_contract.volume_discount(3) == 0.10
        assert bulk_contract.volume_discount(10) == 0.20
        assert bulk_contract.volume_discount(30) == 0.30
        assert bulk_contract.volume_discount(150) == 0.40

    def test_quote_pro_30_seats(self) -> None:
        q = bulk_contract.quote(PlanTier.PRO, 30)
        assert q.discount_rate == 0.30
        assert q.unit_price_jpy < q.list_price_per_seat_jpy
        assert q.monthly_total_jpy == q.unit_price_jpy * 30
        assert q.annual_total_jpy == q.monthly_total_jpy * 12

    def test_agency_margin(self) -> None:
        q = bulk_contract.quote(PlanTier.STARTER, 10, via_agency=True)
        assert q.agency_margin_jpy is not None
        assert q.agency_margin_jpy == int(round(q.monthly_total_jpy * 0.20))

    def test_free_rejected(self) -> None:
        with pytest.raises(ValueError):
            bulk_contract.quote(PlanTier.FREE, 10)

    def test_below_min_seats_rejected(self) -> None:
        with pytest.raises(ValueError):
            bulk_contract.quote(PlanTier.PRO, 2)


class TestBulkQuoteEndpoint:
    def test_public_quote(self) -> None:
        with TestClient(app) as client:
            res = client.post(
                "/api/billing/bulk-quote",
                json={"tier": "pro", "seats": 30},
            )
            assert res.status_code == 200
            body = res.json()
            assert body["discount_rate"] == 0.30
            assert body["monthly_total_jpy"] > 0

    def test_invalid_seats_422(self) -> None:
        with TestClient(app) as client:
            res = client.post(
                "/api/billing/bulk-quote",
                json={"tier": "pro", "seats": 1},
            )
            assert res.status_code == 422
