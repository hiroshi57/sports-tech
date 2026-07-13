"""スコア信頼性ユーティリティ(外販ロードマップ A #2)。

confidence(0〜1) から、スコアの誤差レンジ(±点)と信頼度ラベルを算出する。
外販時に「このスコアはどれくらい信用できるか」を数値で提示するための共通ロジック。

方針:
- confidence が高いほど誤差は小さい。
- 誤差(±) = MAX_MARGIN * (1 - confidence) を基本に、下限/上限でクリップ。
- 実データによるキャリブレーションは A #1(コーチ評価との相関検証)で更新する前提。
"""

from __future__ import annotations

# 誤差レンジの上限（confidence=0 のとき ±この値）
MAX_ERROR_MARGIN = 25.0
# 誤差レンジの下限（confidence=1 でも最低これだけの不確実性は残す）
MIN_ERROR_MARGIN = 3.0


def error_margin(confidence: float) -> float:
    """confidence(0〜1) から誤差レンジ(±点)を算出する。"""
    c = max(0.0, min(1.0, confidence))
    margin = MAX_ERROR_MARGIN * (1.0 - c)
    return round(max(MIN_ERROR_MARGIN, margin), 1)


def reliability_level(confidence: float) -> str:
    """confidence から信頼度ラベルを返す（high / moderate / low）。"""
    c = max(0.0, min(1.0, confidence))
    if c >= 0.7:
        return "high"
    if c >= 0.4:
        return "moderate"
    return "low"


def reliability_note(confidence: float) -> str:
    """信頼度に応じた日本語の注記を返す。"""
    level = reliability_level(confidence)
    if level == "high":
        return "十分なデータ品質で算出された参考スコアです。"
    if level == "moderate":
        return "データ品質は中程度です。撮影条件の改善で精度が上がります。"
    return (
        "データ品質が低く不確実性が大きい参考値です。"
        "推奨条件（正面・全身・30fps以上）での再撮影を推奨します。"
    )
