"""スコア信頼性ユーティリティの単体テスト(A #2)。"""

from __future__ import annotations

from app.services import reliability


class TestErrorMargin:
    def test_high_confidence_small_margin(self) -> None:
        assert reliability.error_margin(1.0) == reliability.MIN_ERROR_MARGIN

    def test_low_confidence_large_margin(self) -> None:
        # confidence 0.1（スタブ）は大きな誤差
        assert reliability.error_margin(0.1) > 15

    def test_monotonic(self) -> None:
        """confidence が上がるほど誤差は縮む（単調）。"""
        margins = [reliability.error_margin(c / 10) for c in range(0, 11)]
        assert margins == sorted(margins, reverse=True)

    def test_clipped_range(self) -> None:
        for c in (0.0, 0.5, 1.0):
            m = reliability.error_margin(c)
            assert reliability.MIN_ERROR_MARGIN <= m <= reliability.MAX_ERROR_MARGIN


class TestReliabilityLevel:
    def test_levels(self) -> None:
        assert reliability.reliability_level(0.9) == "high"
        assert reliability.reliability_level(0.5) == "moderate"
        assert reliability.reliability_level(0.1) == "low"

    def test_note_matches_level(self) -> None:
        assert "再撮影" in reliability.reliability_note(0.1)
        assert reliability.reliability_note(0.9)
