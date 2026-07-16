"""料金プラン・フリーミアム設計の単一の真実の源(外販 E#36 / E#38)。

プラン定義（価格・クォータ・機能フラグ）をコードで一元管理する。
バックエンドの利用制限判定・課金・フロントの料金表がすべてここを参照する。

- 選手数課金 + 分析本数の従量（超過分は overage 単価）というハイブリッド。
- フリーミアム（FREE）は入口を無料にして PRO への転換を狙う設計。
- ENTERPRISE は請求書払い（B2B 商習慣）・無制限・個別見積。

金額はすべて日本円（税抜・月額）。`None` は「無制限 / 個別見積」を表す。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class PlanTier(str, enum.Enum):
    """料金プランの区分。"""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Feature(str, enum.Enum):
    """機能フラグ（プランごとの解放範囲）。"""

    BASIC_SCORE = "basic_score"  # 4項目スコア + レーダー
    SCORE_HISTORY = "score_history"  # 履歴グラフ
    COMPARE = "compare"  # 複数選手比較(C#21)
    REPORT_EXPORT = "report_export"  # PDF/Excelレポート(C#24)
    GROWTH_PREDICTION = "growth_prediction"  # 成長予測(B#20)
    SAVED_SEARCH_ALERT = "saved_search_alert"  # 保存検索・新着アラート(C#23)
    WATCHLIST = "watchlist"  # ウォッチリスト(C#22)
    API_ACCESS = "api_access"  # API連携
    SSO = "sso"  # SSO/SAML
    PRIORITY_SUPPORT = "priority_support"  # 優先サポート


@dataclass(frozen=True)
class Plan:
    """1プランの定義。"""

    tier: PlanTier
    name: str
    monthly_price_jpy: int | None  # None = 個別見積(ENTERPRISE)
    max_athletes: int | None  # 登録できる選手数（None=無制限）
    monthly_analyses: int | None  # 月あたり分析本数の基本枠（None=無制限）
    overage_price_jpy: int | None  # 基本枠超過1本あたり（None=超過不可 or 見積）
    features: frozenset[Feature]
    invoice_payment: bool = False  # 請求書払い可否（B2B）
    description: str = ""
    highlights: list[str] = field(default_factory=list)

    def has_feature(self, feature: Feature) -> bool:
        return feature in self.features

    def allows_overage(self) -> bool:
        return self.overage_price_jpy is not None or self.monthly_analyses is None


# ── プランカタログ本体 ────────────────────────────────────────────────

_CORE = frozenset({Feature.BASIC_SCORE})
_STARTER = _CORE | {
    Feature.SCORE_HISTORY,
    Feature.COMPARE,
    Feature.WATCHLIST,
    Feature.REPORT_EXPORT,
}
_PRO = _STARTER | {
    Feature.GROWTH_PREDICTION,
    Feature.SAVED_SEARCH_ALERT,
    Feature.PRIORITY_SUPPORT,
}
_ENTERPRISE = _PRO | {Feature.API_ACCESS, Feature.SSO}


PLANS: dict[PlanTier, Plan] = {
    PlanTier.FREE: Plan(
        tier=PlanTier.FREE,
        name="Free",
        monthly_price_jpy=0,
        max_athletes=3,
        monthly_analyses=3,
        overage_price_jpy=None,  # 無料枠は超過不可（PROへの転換点）
        features=_CORE,
        description="まず試すための無料枠。選手3人・分析3本/月まで。",
        highlights=["選手3人まで", "分析3本/月", "基本スコア＆レーダー"],
    ),
    PlanTier.STARTER: Plan(
        tier=PlanTier.STARTER,
        name="Starter",
        monthly_price_jpy=9_800,
        max_athletes=20,
        monthly_analyses=30,
        overage_price_jpy=300,
        features=_STARTER,
        description="個人スカウト・小規模スクール向け。比較とレポート出力まで。",
        highlights=["選手20人まで", "分析30本/月（超過¥300/本）", "比較・レポート出力"],
    ),
    PlanTier.PRO: Plan(
        tier=PlanTier.PRO,
        name="Pro",
        monthly_price_jpy=49_800,
        max_athletes=100,
        monthly_analyses=200,
        overage_price_jpy=250,
        features=_PRO,
        invoice_payment=True,
        description="クラブ・スカウト会社向け。成長予測・新着アラート・全分析機能。",
        highlights=[
            "選手100人まで",
            "分析200本/月（超過¥250/本）",
            "成長予測・新着アラート・優先サポート",
        ],
    ),
    PlanTier.ENTERPRISE: Plan(
        tier=PlanTier.ENTERPRISE,
        name="Enterprise",
        monthly_price_jpy=None,  # 個別見積
        max_athletes=None,
        monthly_analyses=None,
        overage_price_jpy=None,
        features=_ENTERPRISE,
        invoice_payment=True,
        description="協会・自治体・大規模クラブ向け。無制限・API/SSO・請求書払い。",
        highlights=["選手・分析 無制限", "API連携・SSO", "請求書払い・個別サポート"],
    ),
}

# フリーミアムの起点（未契約ユーザーに割り当てる既定プラン）
DEFAULT_TIER = PlanTier.FREE


def get_plan(tier: PlanTier | str) -> Plan:
    """区分からプラン定義を取得する。"""
    if isinstance(tier, str):
        tier = PlanTier(tier)
    return PLANS[tier]


def all_plans() -> list[Plan]:
    """料金表表示用に全プランを表示順で返す。"""
    return [PLANS[t] for t in (PlanTier.FREE, PlanTier.STARTER, PlanTier.PRO, PlanTier.ENTERPRISE)]
