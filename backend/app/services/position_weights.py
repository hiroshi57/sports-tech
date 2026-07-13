"""ポジション別のスコア重み付けモデル(外販 B#18)。

ポジションによって重視される能力は異なる。
- FW: 決定力に直結するスプリント/ボールコントロール重視
- MF: 攻守に関わるためバランス型（ポジショニングも高め）
- DF: 対人・カバーのポジショニング/身体の使い方重視
- GK: 身体の使い方（反応・姿勢）とポジショニング重視

重みは各ポジションで合計 1.0。未知/未設定は balanced（0.3/0.3/0.2/0.2）。
実データ検証(A#1)後にキャリブレーションする前提。
"""

from __future__ import annotations

# key: sprint / ball_control / positioning / body_usage
BALANCED: dict[str, float] = {
    "sprint": 0.3,
    "ball_control": 0.3,
    "positioning": 0.2,
    "body_usage": 0.2,
}

WEIGHTS_BY_POSITION: dict[str, dict[str, float]] = {
    "FW": {"sprint": 0.35, "ball_control": 0.35, "positioning": 0.20, "body_usage": 0.10},
    "MF": {"sprint": 0.25, "ball_control": 0.30, "positioning": 0.30, "body_usage": 0.15},
    "DF": {"sprint": 0.20, "ball_control": 0.15, "positioning": 0.35, "body_usage": 0.30},
    "GK": {"sprint": 0.10, "ball_control": 0.20, "positioning": 0.35, "body_usage": 0.35},
}


def weights_for(position: str | None) -> dict[str, float]:
    """ポジション（大文字化して照合）に対応する重みを返す。未知は balanced。"""
    if position is None:
        return dict(BALANCED)
    return dict(WEIGHTS_BY_POSITION.get(position.strip().upper(), BALANCED))


def weighted_total(
    sprint: float,
    ball_control: float,
    positioning: float,
    body_usage: float,
    position: str | None = None,
) -> float:
    """ポジション重みで総合スコアを算出する（小数第1位）。"""
    w = weights_for(position)
    total = (
        sprint * w["sprint"]
        + ball_control * w["ball_control"]
        + positioning * w["positioning"]
        + body_usage * w["body_usage"]
    )
    return round(total, 1)
