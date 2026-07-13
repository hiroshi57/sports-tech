"""ポジション別重み付けモデル(B#18)の単体テスト。"""

from __future__ import annotations

from app.services import position_weights


class TestWeightsFor:
    def test_known_positions_sum_to_one(self) -> None:
        for pos in ("FW", "MF", "DF", "GK"):
            w = position_weights.weights_for(pos)
            assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_unknown_falls_back_to_balanced(self) -> None:
        assert position_weights.weights_for("XX") == position_weights.BALANCED
        assert position_weights.weights_for(None) == position_weights.BALANCED

    def test_case_insensitive(self) -> None:
        assert position_weights.weights_for("fw") == position_weights.weights_for("FW")


class TestWeightedTotal:
    def test_fw_emphasizes_attack(self) -> None:
        """攻撃力が高くポジショニングが低い選手は FW 重みの方が高く出る。"""
        s = dict(sprint=90, ball_control=90, positioning=40, body_usage=40)
        fw = position_weights.weighted_total(**s, position="FW")
        df = position_weights.weighted_total(**s, position="DF")
        assert fw > df

    def test_gk_emphasizes_body_positioning(self) -> None:
        s = dict(sprint=40, ball_control=40, positioning=90, body_usage=90)
        gk = position_weights.weighted_total(**s, position="GK")
        fw = position_weights.weighted_total(**s, position="FW")
        assert gk > fw

    def test_balanced_matches_legacy(self) -> None:
        # 旧来の 0.3/0.3/0.2/0.2
        expected = round(80 * 0.3 + 70 * 0.3 + 60 * 0.2 + 50 * 0.2, 1)
        assert position_weights.weighted_total(80, 70, 60, 50, None) == expected
