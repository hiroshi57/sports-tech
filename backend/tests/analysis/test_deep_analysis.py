"""深掘り分析(B#11-17,19)の単体テスト。"""

from __future__ import annotations

from app.services import deep_analysis

_HIGH = {
    "sprint_score": 90.0,
    "ball_control_score": 88.0,
    "positioning_score": 85.0,
    "body_usage_score": 87.0,
}
_LOW = {
    "sprint_score": 45.0,
    "ball_control_score": 40.0,
    "positioning_score": 42.0,
    "body_usage_score": 44.0,
}


class TestAbilities:
    def test_fourteen_items(self) -> None:
        items = deep_analysis.compute_abilities(_HIGH)
        assert len(items) == 14
        assert all(0 <= i.value <= 100 for i in items)

    def test_high_scores_higher_than_low(self) -> None:
        hi = deep_analysis.compute_abilities(_HIGH)
        lo = deep_analysis.compute_abilities(_LOW)
        assert all(h.value > low.value for h, low in zip(hi, lo, strict=True))


class TestDuelAndSituational:
    def test_duel_in_range(self) -> None:
        d = deep_analysis.compute_duel(_HIGH)
        assert 0 <= d.attacking_1v1 <= 100
        assert d.comment

    def test_situational_best_comment(self) -> None:
        s = deep_analysis.compute_situational(_HIGH)
        assert "局面" in s.comment


class TestFootedness:
    def test_weak_foot_below_dominant(self) -> None:
        f = deep_analysis.compute_footedness(_HIGH)
        assert f.weak_foot_skill < f.dominant_foot_skill
        assert 0 <= f.balance_pct <= 100


class TestHeatmap:
    def test_zones_sum_near_100(self) -> None:
        h = deep_analysis.compute_heatmap("FW", _HIGH)
        total = sum(sum(row) for row in h.zones)
        assert 90 <= total <= 110  # 平滑化で多少ずれる

    def test_fw_attacks_more_than_df(self) -> None:
        fw = deep_analysis.compute_heatmap("FW", _HIGH)
        df = deep_analysis.compute_heatmap("DF", _HIGH)
        assert sum(fw.zones[2]) > sum(df.zones[2])  # 敵陣行


class TestSetPieceAndFatigue:
    def test_height_bonus_aerial(self) -> None:
        tall = deep_analysis.compute_set_piece(_HIGH, 190.0)
        short = deep_analysis.compute_set_piece(_HIGH, 160.0)
        assert tall.aerial_duel > short.aerial_duel

    def test_fatigue_curve_monotonic(self) -> None:
        f = deep_analysis.compute_fatigue(_HIGH, 80.0)
        assert len(f.curve) == 6
        assert all(a >= b for a, b in zip(f.curve, f.curve[1:], strict=False))
        assert f.curve[0] == 100.0

    def test_low_stamina_drops_more(self) -> None:
        strong = deep_analysis.compute_fatigue(_HIGH, 90.0)
        weak = deep_analysis.compute_fatigue(_LOW, 40.0)
        assert strong.endurance_index > weak.endurance_index


class TestAnalyze:
    def test_full_bundle(self) -> None:
        da = deep_analysis.analyze(
            sprint_score=70,
            ball_control_score=72,
            positioning_score=68,
            body_usage_score=71,
            position="MF",
            height_cm=172.0,
            consistency=75.0,
        )
        assert len(da.abilities) == 14
        assert da.heatmap.zones
        assert da.fatigue.curve
