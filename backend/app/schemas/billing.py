"""課金・サブスクリプション関連スキーマ(外販 E#36-39)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    """料金表の1プラン。"""

    tier: str
    name: str
    monthly_price_jpy: int | None  # None=個別見積
    max_athletes: int | None  # None=無制限
    monthly_analyses: int | None  # None=無制限
    overage_price_jpy: int | None
    invoice_payment: bool
    features: list[str]
    description: str
    highlights: list[str]


class SubscriptionResponse(BaseModel):
    """現在の契約状況 + 当期利用量。"""

    plan_tier: str
    plan_name: str
    status: str
    billing_type: str
    analyses_used: int
    monthly_analyses: int | None  # 基本枠（None=無制限）
    analyses_remaining: int | None  # 残枠（None=無制限）
    max_athletes: int | None


class CheckoutRequest(BaseModel):
    """カード決済のチェックアウト開始リクエスト。"""

    tier: str = Field(..., description="申込プラン(starter/pro/enterprise)")
    success_url: str = Field("https://web-kappa-steel-92.vercel.app/billing?ok=1")
    cancel_url: str = Field("https://web-kappa-steel-92.vercel.app/pricing")


class CheckoutResponse(BaseModel):
    """チェックアウト結果。"""

    checkout_url: str | None  # Stripe Checkout URL（manualモードでは None）
    mode: str  # "stripe" | "manual"
    message: str


class InvoiceRequest(BaseModel):
    """請求書払い（B2B）の申込リクエスト。"""

    tier: str = Field(..., description="申込プラン(pro/enterprise)")
    company_name: str = Field(..., min_length=1, max_length=200)
    contact_email: str = Field(..., max_length=255)
    note: str | None = Field(None, max_length=1000)


class BulkQuoteRequest(BaseModel):
    """一括契約(E#40)の見積リクエスト。"""

    tier: str = Field(..., description="starter / pro")
    seats: int = Field(..., ge=1, le=10000, description="契約席数（アカウント数）")
    via_agency: bool = Field(False, description="代理店経由か")


class BulkQuoteResponse(BaseModel):
    """一括契約の見積結果。"""

    tier: str
    seats: int
    list_price_per_seat_jpy: int
    discount_rate: float
    unit_price_jpy: int
    monthly_total_jpy: int
    annual_total_jpy: int
    agency_margin_jpy: int | None
    notes: list[str]
