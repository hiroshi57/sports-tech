"""ポーズ時系列からスコアを算出する（純関数群）。

各スコアは 0〜100。ここでのロジックは Phase 1 のヒューリスティックであり、
専門コーチ評価との相関検証（外販ロードマップ #21）を経て #4〜#7 で
本格的なモデルに差し替える。

設計方針:
- ランドマークの運動学的特徴量（速度・安定性・可動域）から算出する
- ボール検出は未実装のため ball_control は下肢の動きの滑らかさで近似する
  （限界を confidence と feedback に明記する）
"""

from __future__ import annotations

import math
import statistics

from app.services.pose_estimation import (
    LM_LEFT_ANKLE,
    LM_LEFT_HIP,
    LM_LEFT_KNEE,
    LM_LEFT_SHOULDER,
    LM_RIGHT_ANKLE,
    LM_RIGHT_HIP,
    LM_RIGHT_KNEE,
    LM_RIGHT_SHOULDER,
    Landmark,
    PoseSequence,
)

# スコアリングに必要な最小フレーム数
MIN_FRAMES_FOR_SCORING = 5

# ボール未検出による近似スコアの信頼度上限
BALL_CONTROL_CONFIDENCE_CAP = 0.4


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _midpoint(a: Landmark, b: Landmark) -> tuple[float, float]:
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)


def _velocities(points: list[tuple[float, float]], fps: float) -> list[float]:
    """連続点間の速度（正規化座標/秒）のリストを返す。"""
    if fps <= 0 or len(points) < 2:
        return []
    vels: list[float] = []
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        dist = math.hypot(x1 - x0, y1 - y0)
        vels.append(dist * fps)
    return vels


def _hip_centers(seq: PoseSequence) -> list[tuple[float, float]]:
    return [_midpoint(f.landmarks[LM_LEFT_HIP], f.landmarks[LM_RIGHT_HIP]) for f in seq.frames]


def _accelerations(vels: list[float], fps: float) -> list[float]:
    """速度列から加速度（速度変化 × fps）の絶対値リストを返す。"""
    if fps <= 0 or len(vels) < 2:
        return []
    return [abs(v1 - v0) * fps for v0, v1 in zip(vels, vels[1:], strict=False)]


def _direction_changes(points: list[tuple[float, float]], min_move: float = 0.01) -> int:
    """
    水平方向の進行方向が反転した回数を数える（アジリティの代理指標）。

    min_move 未満の微小移動はノイズとして無視する。
    """
    if len(points) < 3:
        return 0
    dxs = [
        x1 - x0
        for (x0, _), (x1, _) in zip(points, points[1:], strict=False)
        if abs(x1 - x0) >= min_move
    ]
    changes = 0
    for a, b in zip(dxs, dxs[1:], strict=False):
        if (a < 0 < b) or (a > 0 > b):
            changes += 1
    return changes


def compute_sprint_score(seq: PoseSequence) -> float:
    """
    スプリントスコア(#4): 最大速度・加速力（バースト）・ケイデンスから算出。

    - 最大速度: トップスピードの高さ
    - 加速力: 静止から一気に加速できるか（上位加速度）
    - ケイデンス: 脚の回転の速さ（膝の上下動頻度）

    速い + 素早く加速 + 高回転 = 高スコア。
    """
    hips = _hip_centers(seq)
    vels = _velocities(hips, seq.fps)
    if not vels:
        return 0.0

    # 最大速度（外れ値対策で上位平均を使う）
    top = sorted(vels, reverse=True)[: max(1, len(vels) // 5)]
    max_speed = statistics.mean(top)

    # 加速力: 加速度の上位平均（バースト力）
    accels = _accelerations(vels, seq.fps)
    if accels:
        top_acc = sorted(accels, reverse=True)[: max(1, len(accels) // 5)]
        max_accel = statistics.mean(top_acc)
    else:
        max_accel = 0.0

    # ケイデンス: 膝の上下動のゼロ交差回数（片脚）
    knee_ys = [f.landmarks[LM_LEFT_KNEE].y for f in seq.frames]
    cadence = _oscillation_rate(knee_ys, seq.fps)

    # 正規化: 経験的スケール（Phase 1 ヒューリスティック）
    speed_component = _clamp(max_speed / 0.8 * 100.0)  # 0.8/s で満点付近
    accel_component = _clamp(max_accel / 4.0 * 100.0)  # 4.0/s^2 で満点付近
    cadence_component = _clamp(cadence / 3.0 * 100.0)  # 3Hz で満点付近

    return round(
        _clamp(speed_component * 0.5 + accel_component * 0.2 + cadence_component * 0.3),
        1,
    )


def compute_body_usage_score(seq: PoseSequence) -> float:
    """
    身体の使い方スコア(#7): 体幹安定性・左右対称性・上下動の効率から算出。

    - 体幹安定性: 肩-腰の傾きの一貫性（ブレが小さいほど良い）
    - 左右対称性: 左右の膝の高さ差（小さいほど良い）
    - 上下動効率: 腰の無駄な上下バウンドが小さいほど良い（省エネな走り）
    """
    torso_angles: list[float] = []
    for f in seq.frames:
        shoulder = _midpoint(f.landmarks[LM_LEFT_SHOULDER], f.landmarks[LM_RIGHT_SHOULDER])
        hip = _midpoint(f.landmarks[LM_LEFT_HIP], f.landmarks[LM_RIGHT_HIP])
        angle = math.atan2(shoulder[1] - hip[1], shoulder[0] - hip[0])
        torso_angles.append(angle)

    if len(torso_angles) < 2:
        return 0.0

    # 体幹角度の標準偏差（小さいほど安定）
    stability_std = statistics.pstdev(torso_angles)
    # 0 rad で満点、0.5 rad 以上で 0 点付近
    stability_component = _clamp((1.0 - stability_std / 0.5) * 100.0)

    # 左右対称性: 左右膝の高さ差の平均（小さいほど対称）
    knee_diffs = [
        abs(f.landmarks[LM_LEFT_KNEE].y - f.landmarks[LM_RIGHT_KNEE].y) for f in seq.frames
    ]
    symmetry_component = _clamp((1.0 - statistics.mean(knee_diffs) / 0.3) * 100.0)

    # 上下動効率: 腰の垂直位置の標準偏差（大きいほど無駄なバウンドが多い）
    hip_ys = [_midpoint(f.landmarks[LM_LEFT_HIP], f.landmarks[LM_RIGHT_HIP])[1] for f in seq.frames]
    bounce_std = statistics.pstdev(hip_ys)
    efficiency_component = _clamp((1.0 - bounce_std / 0.1) * 100.0)  # 0.1 以上で 0 点付近

    return round(
        _clamp(stability_component * 0.45 + symmetry_component * 0.3 + efficiency_component * 0.25),
        1,
    )


def compute_positioning_score(seq: PoseSequence) -> float:
    """
    ポジショニングスコア: フィールド内の移動範囲（活動量）から算出。

    広い範囲をカバー = 高スコア（オフザボールの動きの多さを近似）。
    """
    hips = _hip_centers(seq)
    if len(hips) < 2:
        return 0.0

    xs = [p[0] for p in hips]
    ys = [p[1] for p in hips]
    coverage = (max(xs) - min(xs)) * (max(ys) - min(ys))  # バウンディングボックス面積

    # 総移動距離
    total_dist = sum(
        math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(hips, hips[1:], strict=False)
    )

    # 方向転換回数（アジリティ: 動き直し・切り返しの多さ）
    dir_changes = _direction_changes(hips)
    duration = seq.duration_sec or 1.0
    agility_rate = dir_changes / duration  # 回/秒

    coverage_component = _clamp(coverage / 0.15 * 100.0)  # 面積 0.15 で満点付近
    distance_component = _clamp(total_dist / 3.0 * 100.0)  # 累積 3.0 で満点付近
    agility_component = _clamp(agility_rate / 1.5 * 100.0)  # 1.5回/秒 で満点付近

    return round(
        _clamp(coverage_component * 0.4 + distance_component * 0.4 + agility_component * 0.2),
        1,
    )


def compute_ball_control_score(seq: PoseSequence) -> float:
    """
    ボールコントロールスコア（近似）: 足首の動きの滑らかさ（加速度の小ささ）から算出。

    NOTE:
        ボール物体検出が未実装のため、下肢の細かい制御動作を代理指標とする。
        本来のボールタッチ精度とは異なるため confidence を抑える。
    """
    ankle_points = [
        _midpoint(f.landmarks[LM_LEFT_ANKLE], f.landmarks[LM_RIGHT_ANKLE]) for f in seq.frames
    ]
    vels = _velocities(ankle_points, seq.fps)
    if len(vels) < 2:
        return 0.0

    # 加速度（速度の変化量）の平均が小さい = 滑らかな制御
    accels = [abs(v1 - v0) for v0, v1 in zip(vels, vels[1:], strict=False)]
    mean_accel = statistics.mean(accels)
    smoothness = _clamp((1.0 - mean_accel / 0.5) * 100.0)

    # 適度な動きの量（動かなさすぎず）
    activity = _clamp(statistics.mean(vels) / 0.4 * 100.0)

    return round(_clamp(smoothness * 0.7 + activity * 0.3), 1)


def _oscillation_rate(values: list[float], fps: float) -> float:
    """時系列の平均値まわりのゼロ交差から振動周波数（Hz）を推定する。"""
    if len(values) < 2 or fps <= 0:
        return 0.0
    mean = statistics.mean(values)
    centered = [v - mean for v in values]
    crossings = 0
    for a, b in zip(centered, centered[1:], strict=False):
        if a == 0:
            continue
        if (a < 0 < b) or (a > 0 > b):
            crossings += 1
    # ゼロ交差 2 回で 1 周期
    cycles = crossings / 2.0
    duration = len(values) / fps
    return cycles / duration if duration > 0 else 0.0
