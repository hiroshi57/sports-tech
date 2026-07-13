"""スコア根拠の可視化(外販 A #8)。

総合スコアは 4 つの能力スコアの加重平均。
「どの能力がどれだけ総合点に効いているか」を内訳として返し、
スカウトが『なぜこの総合スコアなのか』を理解できるようにする。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services import position_weights

# balanced 重み（後方互換の既定）。ポジション別は position_weights を参照。
SCORE_WEIGHTS: dict[str, float] = {
    "sprint_score": 0.3,
    "ball_control_score": 0.3,
    "positioning_score": 0.2,
    "body_usage_score": 0.2,
}

_LABELS: dict[str, str] = {
    "sprint_score": "スプリント",
    "ball_control_score": "ボールコントロール",
    "positioning_score": "ポジショニング",
    "body_usage_score": "身体の使い方",
}


@dataclass(frozen=True)
class ScoreFactor:
    key: str
    label: str
    value: float  # 能力スコア 0-100
    weight: float  # 総合への重み
    contribution: float  # value * weight（総合点への寄与ポイント）
    contribution_pct: float  # 総合点に占める割合(%)


def explain_total(
    sprint: float,
    ball_control: float,
    positioning: float,
    body_usage: float,
    position: str | None = None,
) -> list[ScoreFactor]:
    """4 サブスコアから総合スコアへの寄与内訳を算出する（寄与降順・ポジション重み対応）。"""
    values = {
        "sprint_score": sprint,
        "ball_control_score": ball_control,
        "positioning_score": positioning,
        "body_usage_score": body_usage,
    }
    # ポジション重み（sprint/ball_control/... のキー）を *_score キーに対応付け
    pw = position_weights.weights_for(position)
    weights = {
        "sprint_score": pw["sprint"],
        "ball_control_score": pw["ball_control"],
        "positioning_score": pw["positioning"],
        "body_usage_score": pw["body_usage"],
    }
    contributions = {k: values[k] * weights[k] for k in values}
    total = sum(contributions.values())

    factors = [
        ScoreFactor(
            key=k,
            label=_LABELS[k],
            value=round(values[k], 1),
            weight=weights[k],
            contribution=round(contributions[k], 1),
            contribution_pct=round(contributions[k] / total * 100, 1) if total > 0 else 0.0,
        )
        for k in values
    ]
    factors.sort(key=lambda f: f.contribution, reverse=True)
    return factors
