"""成長予測サービス(外販 B#20)。

スコア履歴の傾き（線形トレンド）と年齢によるポテンシャル係数から、
12ヶ月後の総合スコアと伸びしろ(potential)を推定する。
実データ（AnalysisResult 履歴）から算出し、デモの推定を本実装化する。

Phase 1 ヒューリスティック。実測検証は A#1 系で更新する前提。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# 年齢別のポテンシャル基準（若いほど伸びしろ大）
MAX_SCORE = 99.0


@dataclass(frozen=True)
class GrowthPrediction:
    horizon: str
    projected_total: float
    potential: float  # 0-100
    monthly_trend: float  # 直近の月あたり総合スコア変化
    comment: str


def _slope_per_month(totals: list[float]) -> float:
    """総合スコア履歴の1ステップあたり平均変化（単純線形）。"""
    if len(totals) < 2:
        return 0.0
    # 最小二乗の傾き（x=0,1,2,...）
    n = len(totals)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(totals) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, totals, strict=False))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else 0.0


def _age_from_birth(birth: date | None, today: date | None = None) -> int | None:
    if birth is None:
        return None
    today = today or date.today()
    y = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        y -= 1
    return y


def _potential(age: int | None, latest_total: float) -> float:
    """年齢と現在値から伸びしろ(0-100)を推定。若く・現在値が低いほど高い。"""
    # 年齢係数: 15歳以下=1.0, 22歳以上=0.3 の線形
    if age is None:
        age_factor = 0.6
    else:
        age_factor = max(0.3, min(1.0, 1.0 - (age - 15) * 0.1))
    headroom = max(0.0, MAX_SCORE - latest_total) / MAX_SCORE  # 上限までの余地
    return round(min(100.0, (age_factor * 0.7 + headroom * 0.3) * 100), 1)


def predict(
    totals_oldest_first: list[float],
    latest_total: float,
    birth_date: date | None,
    horizon_months: int = 12,
) -> GrowthPrediction:
    """スコア履歴・年齢から将来予測を返す。"""
    slope = _slope_per_month(totals_oldest_first)
    age = _age_from_birth(birth_date)
    potential = _potential(age, latest_total)

    # トレンド寄与 + ポテンシャル寄与（ポテンシャルが高いほど上振れ）
    trend_gain = slope * horizon_months
    potential_gain = (potential / 100.0) * (horizon_months / 12.0) * 6.0  # 最大 ~6pt/年
    projected = round(min(MAX_SCORE, latest_total + trend_gain + potential_gain), 1)

    if age is not None and age <= 17:
        comment = "成長期。フィジカル向上の余地が大きく、総合スコアの上振れが期待できる。"
    elif slope > 0.3:
        comment = "直近の伸びが顕著。現在の取り組みを継続すれば更なる向上が見込める。"
    elif slope < -0.3:
        comment = "直近はやや下降。コンディションや負荷管理の見直しを推奨。"
    else:
        comment = "安定推移。技術面の重点強化で伸びしろを引き出せる。"

    return GrowthPrediction(
        horizon=f"{horizon_months}ヶ月後",
        projected_total=projected,
        potential=potential,
        monthly_trend=round(slope, 2),
        comment=comment,
    )
