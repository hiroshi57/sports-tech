"""スコア根拠の可視化(A #8)の単体テスト。"""

from __future__ import annotations

from app.services import score_explain


class TestExplainTotal:
    def test_returns_four_factors(self) -> None:
        factors = score_explain.explain_total(80, 70, 60, 50)
        assert len(factors) == 4

    def test_sorted_by_contribution_desc(self) -> None:
        factors = score_explain.explain_total(80, 70, 60, 50)
        contribs = [f.contribution for f in factors]
        assert contribs == sorted(contribs, reverse=True)

    def test_contribution_is_value_times_weight(self) -> None:
        factors = score_explain.explain_total(80, 70, 60, 50)
        sprint = next(f for f in factors if f.key == "sprint_score")
        assert sprint.contribution == round(80 * 0.3, 1)

    def test_pct_sums_to_100(self) -> None:
        factors = score_explain.explain_total(80, 70, 60, 50)
        total_pct = sum(f.contribution_pct for f in factors)
        assert 99.0 <= total_pct <= 101.0

    def test_weights_match_engine(self) -> None:
        """総合スコアの重み合計は 1.0。"""
        assert abs(sum(score_explain.SCORE_WEIGHTS.values()) - 1.0) < 1e-9

    def test_zero_scores_no_crash(self) -> None:
        factors = score_explain.explain_total(0, 0, 0, 0)
        assert all(f.contribution_pct == 0.0 for f in factors)
