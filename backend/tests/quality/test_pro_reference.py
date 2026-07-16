"""プロ水準リファレンスDB(A#7)の単体テスト。"""

from __future__ import annotations

from app.services import pro_reference


class TestProReference:
    def test_known_position_profile(self) -> None:
        prof = pro_reference.get_profile("FW")
        assert prof["sprint_score"] == 92.0

    def test_unknown_position_uses_default(self) -> None:
        prof = pro_reference.get_profile("XYZ")
        assert prof == pro_reference.get_profile(None)

    def test_attainment_capped_at_100(self) -> None:
        # 基準を超えるスコアでも到達度は100で頭打ち
        ev = pro_reference.evaluate("FW", {m: 100.0 for m in pro_reference._METRICS})
        assert all(v <= 100.0 for v in ev.attainment.values())
        assert ev.overall_attainment <= 100.0

    def test_gap_positive_when_below(self) -> None:
        ev = pro_reference.evaluate(
            "MF",
            {
                "sprint_score": 50.0,
                "ball_control_score": 50.0,
                "positioning_score": 50.0,
                "body_usage_score": 50.0,
            },
        )
        assert all(g > 0 for g in ev.gap.values())
        assert ev.overall_attainment < 100.0

    def test_all_profiles_has_four_positions(self) -> None:
        profs = pro_reference.all_profiles()
        assert set(profs.keys()) == {"FW", "MF", "DF", "GK"}
