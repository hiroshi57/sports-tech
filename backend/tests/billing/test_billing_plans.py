"""料金プラン catalog の単体テスト(E#36 / E#38)。"""

from __future__ import annotations

from app.services import billing_plans
from app.services.billing_plans import Feature, PlanTier


class TestPlanCatalog:
    def test_all_plans_ordered(self) -> None:
        tiers = [p.tier for p in billing_plans.all_plans()]
        assert tiers == [PlanTier.FREE, PlanTier.STARTER, PlanTier.PRO, PlanTier.ENTERPRISE]

    def test_free_is_zero_and_no_overage(self) -> None:
        free = billing_plans.get_plan(PlanTier.FREE)
        assert free.monthly_price_jpy == 0
        assert free.allows_overage() is False  # PROへの転換点
        assert free.max_athletes == 3
        assert free.monthly_analyses == 3

    def test_enterprise_unlimited_and_invoice(self) -> None:
        ent = billing_plans.get_plan(PlanTier.ENTERPRISE)
        assert ent.monthly_price_jpy is None  # 個別見積
        assert ent.max_athletes is None
        assert ent.monthly_analyses is None
        assert ent.invoice_payment is True
        assert ent.allows_overage() is True  # 無制限

    def test_feature_gating_is_monotonic(self) -> None:
        free = billing_plans.get_plan(PlanTier.FREE)
        pro = billing_plans.get_plan(PlanTier.PRO)
        # 成長予測は PRO 以上のみ
        assert free.has_feature(Feature.GROWTH_PREDICTION) is False
        assert pro.has_feature(Feature.GROWTH_PREDICTION) is True
        # 上位は下位の機能をすべて含む
        assert free.features <= pro.features

    def test_string_lookup(self) -> None:
        assert billing_plans.get_plan("starter").tier == PlanTier.STARTER
