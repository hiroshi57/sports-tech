"""プロ水準リファレンスDB(外販 A#7)。

ポジション別に「プロ/トップ水準の基準プロファイル」を定義し、
育成年代の選手スコアを絶対的な基準点と比較できるようにする。

同ポジション“平均”との比較(compute_analytics)は相対評価だが、
本モジュールはトップ選手像との“到達度”を示す絶対基準を提供する。

数値は Phase 1 のヒューリスティック基準。将来 A#7 実データ（プロ選手の
リファレンス計測）で更新する前提。スコアは常に参考値。
"""

from __future__ import annotations

from dataclasses import dataclass

# ポジション別のプロ水準リファレンス（4基礎スコアの目安・0-100）
# FW=決定力/仕掛け, MF=展開/技術, DF=対人/ポジショニング, GK=反応/ハイボール
_PRO_PROFILES: dict[str, dict[str, float]] = {
    "FW": {
        "sprint_score": 92.0,
        "ball_control_score": 88.0,
        "positioning_score": 90.0,
        "body_usage_score": 86.0,
    },
    "MF": {
        "sprint_score": 84.0,
        "ball_control_score": 92.0,
        "positioning_score": 90.0,
        "body_usage_score": 85.0,
    },
    "DF": {
        "sprint_score": 86.0,
        "ball_control_score": 82.0,
        "positioning_score": 92.0,
        "body_usage_score": 90.0,
    },
    "GK": {
        "sprint_score": 78.0,
        "ball_control_score": 80.0,
        "positioning_score": 93.0,
        "body_usage_score": 91.0,
    },
}

# ポジション不明・その他向けの汎用基準
_DEFAULT_PROFILE: dict[str, float] = {
    "sprint_score": 86.0,
    "ball_control_score": 86.0,
    "positioning_score": 88.0,
    "body_usage_score": 87.0,
}

_METRICS = (
    "sprint_score",
    "ball_control_score",
    "positioning_score",
    "body_usage_score",
)


@dataclass(frozen=True)
class ProReference:
    """プロ水準基準と選手スコアの到達度。"""

    position: str
    reference: dict[str, float]  # プロ水準の各スコア
    attainment: dict[str, float]  # 各項目の到達度(%)＝選手/基準×100
    overall_attainment: float  # 総合到達度(%)
    gap: dict[str, float]  # 各項目の不足(基準-選手, 正=不足)


def get_profile(position: str | None) -> dict[str, float]:
    """ポジションのプロ水準プロファイルを返す（不明時は汎用）。"""
    if position is None:
        return dict(_DEFAULT_PROFILE)
    return dict(_PRO_PROFILES.get(position.upper(), _DEFAULT_PROFILE))


def evaluate(
    position: str | None,
    scores: dict[str, float],
) -> ProReference:
    """選手スコアをプロ水準基準と比較し到達度・ギャップを算出する。"""
    ref = get_profile(position)
    attainment: dict[str, float] = {}
    gap: dict[str, float] = {}
    for m in _METRICS:
        player = float(scores.get(m, 0.0))
        base = ref[m]
        attainment[m] = round(min(100.0, (player / base) * 100), 1) if base else 0.0
        gap[m] = round(max(0.0, base - player), 1)
    overall = round(sum(attainment.values()) / len(_METRICS), 1)
    return ProReference(
        position=(position or "汎用").upper(),
        reference=ref,
        attainment=attainment,
        overall_attainment=overall,
        gap=gap,
    )


def all_profiles() -> dict[str, dict[str, float]]:
    """リファレンスDB全体（ポジション別プロ水準）を返す。"""
    return {pos: dict(prof) for pos, prof in _PRO_PROFILES.items()}
