"""成長予測サービス(B#20)の単体テスト。"""

from __future__ import annotations

from datetime import date

from app.services import growth_service


class TestPredict:
    def test_upward_trend_projects_higher(self) -> None:
        gp = growth_service.predict([60, 65, 70], 70.0, None)
        assert gp.projected_total >= 70.0
        assert gp.monthly_trend > 0

    def test_downward_trend_comment(self) -> None:
        gp = growth_service.predict([80, 75, 70], 70.0, None)
        assert gp.monthly_trend < 0
        assert "下降" in gp.comment

    def test_young_athlete_higher_potential(self) -> None:
        young = growth_service.predict([70, 70], 70.0, date(2010, 1, 1))  # ~16歳
        old = growth_service.predict([70, 70], 70.0, date(2000, 1, 1))  # ~26歳
        assert young.potential > old.potential

    def test_projection_capped(self) -> None:
        gp = growth_service.predict([95, 97, 99], 99.0, date(2010, 1, 1))
        assert gp.projected_total <= growth_service.MAX_SCORE

    def test_single_point_no_trend(self) -> None:
        gp = growth_service.predict([70], 70.0, None)
        assert gp.monthly_trend == 0.0
