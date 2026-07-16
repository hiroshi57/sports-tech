"""代理店・クラブ一括契約プラン(外販 E#40)。

複数アカウント（クラブ/チーム単位の席）をまとめて契約する際の
ボリュームディスカウントと見積を提供する。

- 席数（アカウント数）に応じた割引率を適用
- 代理店（リセラー）にはマージン率を提示
- 支払いは請求書払い（billing_type=invoice, E#37）前提

協会・自治体の「面」導入（F#45）の価格エンジンとなる。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services import billing_plans
from app.services.billing_plans import PlanTier

# 席数レンジ別の割引率（一括契約）
_VOLUME_DISCOUNTS: list[tuple[int, int | None, float]] = [
    # (最小席数, 最大席数(None=上限なし), 割引率)
    (3, 9, 0.10),
    (10, 29, 0.20),
    (30, 99, 0.30),
    (100, None, 0.40),
]

# 代理店マージン率（代理店経由の販売時に代理店へ支払う割合）
AGENCY_MARGIN_RATE = 0.20

# 一括契約の最低席数
MIN_BULK_SEATS = 3


@dataclass(frozen=True)
class BulkQuote:
    tier: str
    seats: int
    list_price_per_seat_jpy: int  # 定価（1席あたり月額）
    discount_rate: float  # 適用割引率
    unit_price_jpy: int  # 割引後の1席あたり月額
    monthly_total_jpy: int  # 月額合計
    annual_total_jpy: int  # 年額合計（12ヶ月）
    agency_margin_jpy: int | None  # 代理店経由時の月次マージン
    notes: list[str]


def volume_discount(seats: int) -> float:
    """席数に応じた割引率を返す。"""
    for lo, hi, rate in _VOLUME_DISCOUNTS:
        if seats >= lo and (hi is None or seats <= hi):
            return rate
    return 0.0


def quote(
    tier: PlanTier | str,
    seats: int,
    *,
    via_agency: bool = False,
) -> BulkQuote:
    """E#40: 一括契約の見積を作成する。

    - Starter/Pro のみ対象（Free は無料、Enterprise は個別見積）
    - 席数 >= MIN_BULK_SEATS
    """
    plan = billing_plans.get_plan(tier)
    if plan.tier in (PlanTier.FREE, PlanTier.ENTERPRISE):
        raise ValueError("一括契約の対象は Starter / Pro です（Enterprise は個別見積）")
    if seats < MIN_BULK_SEATS:
        raise ValueError(f"一括契約は {MIN_BULK_SEATS} 席以上から適用されます")

    list_price = plan.monthly_price_jpy or 0
    rate = volume_discount(seats)
    unit = int(round(list_price * (1.0 - rate), -2))  # 100円単位に丸め
    monthly = unit * seats
    annual = monthly * 12
    margin = int(round(monthly * AGENCY_MARGIN_RATE)) if via_agency else None

    notes = [
        f"{seats}席の一括契約で {int(rate * 100)}% 割引を適用",
        "支払いは請求書払い（月末締め・翌月末払い）に対応",
    ]
    if via_agency:
        notes.append(f"代理店マージン {int(AGENCY_MARGIN_RATE * 100)}% を含む")
    if seats >= 100:
        notes.append("100席以上は Enterprise（個別見積）への切替でさらに最適化可能")

    return BulkQuote(
        tier=plan.tier.value,
        seats=seats,
        list_price_per_seat_jpy=list_price,
        discount_rate=rate,
        unit_price_jpy=unit,
        monthly_total_jpy=monthly,
        annual_total_jpy=annual,
        agency_margin_jpy=margin,
        notes=notes,
    )
