"""姿勢スコアリング（純関数）の単体テスト。

MediaPipe を使わず、合成したポーズ時系列でスコア関数を検証する。
"""

from __future__ import annotations

import math

from app.services import scoring
from app.services.pose_estimation import NUM_LANDMARKS, Landmark, PoseFrame, PoseSequence


def _make_frame(overrides: dict[int, tuple[float, float]]) -> PoseFrame:
    """全ランドマークを (0.5, 0.5) で埋め、指定インデックスのみ上書きする。"""
    lms = [Landmark(x=0.5, y=0.5, z=0.0, visibility=1.0) for _ in range(NUM_LANDMARKS)]
    for idx, (x, y) in overrides.items():
        lms[idx] = Landmark(x=x, y=y, z=0.0, visibility=1.0)
    return PoseFrame(landmarks=lms)


def make_walking_sequence(num_frames: int = 30, fps: float = 15.0) -> PoseSequence:
    """
    右方向に移動しながら脚を上下させる合成シーケンス。

    スプリント / ポジショニングが中〜高、体幹が安定するように作る。
    analysis_engine のポーズパステストからも利用される。
    """
    from app.services.pose_estimation import (
        LM_LEFT_ANKLE,
        LM_LEFT_HIP,
        LM_LEFT_KNEE,
        LM_LEFT_SHOULDER,
        LM_RIGHT_ANKLE,
        LM_RIGHT_HIP,
        LM_RIGHT_KNEE,
        LM_RIGHT_SHOULDER,
    )

    frames: list[PoseFrame] = []
    for i in range(num_frames):
        progress = i / num_frames  # 0 → 1 で右に移動
        base_x = 0.1 + progress * 0.7
        leg_phase = math.sin(i * 0.8) * 0.05  # 脚の上下動

        frames.append(
            _make_frame(
                {
                    LM_LEFT_SHOULDER: (base_x - 0.05, 0.3),
                    LM_RIGHT_SHOULDER: (base_x + 0.05, 0.3),
                    LM_LEFT_HIP: (base_x - 0.04, 0.55),
                    LM_RIGHT_HIP: (base_x + 0.04, 0.55),
                    LM_LEFT_KNEE: (base_x - 0.04, 0.72 + leg_phase),
                    LM_RIGHT_KNEE: (base_x + 0.04, 0.72 - leg_phase),
                    LM_LEFT_ANKLE: (base_x - 0.04, 0.9 + leg_phase),
                    LM_RIGHT_ANKLE: (base_x + 0.04, 0.9 - leg_phase),
                }
            )
        )
    return PoseSequence(frames=frames, fps=fps, width=1280, height=720)


def make_static_sequence(num_frames: int = 30, fps: float = 15.0) -> PoseSequence:
    """全く動かない合成シーケンス（低スプリント・低ポジショニング）。"""
    frame = _make_frame({})
    return PoseSequence(frames=[frame] * num_frames, fps=fps)


class TestScoreRanges:
    def test_all_scores_in_range_for_walking(self) -> None:
        seq = make_walking_sequence()
        assert 0 <= scoring.compute_sprint_score(seq) <= 100
        assert 0 <= scoring.compute_ball_control_score(seq) <= 100
        assert 0 <= scoring.compute_positioning_score(seq) <= 100
        assert 0 <= scoring.compute_body_usage_score(seq) <= 100

    def test_empty_sequence_returns_zero(self) -> None:
        empty = PoseSequence(frames=[], fps=30.0)
        assert scoring.compute_sprint_score(empty) == 0.0
        assert scoring.compute_ball_control_score(empty) == 0.0
        assert scoring.compute_positioning_score(empty) == 0.0
        assert scoring.compute_body_usage_score(empty) == 0.0


class TestSprintScore:
    def test_moving_scores_higher_than_static(self) -> None:
        """動いている方が静止より高いスプリントスコアになる。"""
        moving = scoring.compute_sprint_score(make_walking_sequence())
        static = scoring.compute_sprint_score(make_static_sequence())
        assert moving > static


class TestPositioningScore:
    def test_wide_movement_scores_higher(self) -> None:
        """移動範囲が広い方が高いポジショニングスコアになる。"""
        wide = scoring.compute_positioning_score(make_walking_sequence())
        static = scoring.compute_positioning_score(make_static_sequence())
        assert wide > static


class TestBodyUsageScore:
    def test_stable_posture_scores_high(self) -> None:
        """静止（安定姿勢）は高い身体の使い方スコアになる。"""
        static = scoring.compute_body_usage_score(make_static_sequence())
        assert static > 50


class TestOscillationRate:
    def test_detects_frequency(self) -> None:
        """既知の正弦波の振動周波数を概ね推定できる。"""
        fps = 30.0
        # 2Hz の正弦波を 1 秒分
        values = [math.sin(2 * math.pi * 2 * (i / fps)) for i in range(int(fps))]
        rate = scoring._oscillation_rate(values, fps)
        assert 1.5 <= rate <= 2.5
