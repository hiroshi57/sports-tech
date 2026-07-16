"""課金・サブスクリプション エンドポイント(外販 E#36-38)。

GET  /api/billing/plans           — 料金表（認証不要）
GET  /api/billing/subscription    — 自分の契約状況＋当期利用量
POST /api/billing/checkout        — カード決済チェックアウト開始
POST /api/billing/invoice         — 請求書払い(B2B)の申込
POST /api/billing/webhook         — Stripe Webhook 受信
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.billing import (
    BulkQuoteRequest,
    BulkQuoteResponse,
    CheckoutRequest,
    CheckoutResponse,
    InvoiceRequest,
    PlanResponse,
    SubscriptionResponse,
)
from app.services import billing_plans, billing_service, bulk_contract
from app.services.billing_plans import Plan, PlanTier

router = APIRouter()


def _plan_to_response(p: Plan) -> PlanResponse:
    return PlanResponse(
        tier=p.tier.value,
        name=p.name,
        monthly_price_jpy=p.monthly_price_jpy,
        max_athletes=p.max_athletes,
        monthly_analyses=p.monthly_analyses,
        overage_price_jpy=p.overage_price_jpy,
        invoice_payment=p.invoice_payment,
        features=[f.value for f in sorted(p.features, key=lambda x: x.value)],
        description=p.description,
        highlights=p.highlights,
    )


@router.get("/plans", response_model=list[PlanResponse], summary="料金プラン一覧")
def list_plans() -> list[PlanResponse]:
    """料金表（認証不要・公開）。"""
    return [_plan_to_response(p) for p in billing_plans.all_plans()]


@router.post(
    "/bulk-quote",
    response_model=BulkQuoteResponse,
    summary="一括契約(E#40)の見積を取得する",
)
def bulk_quote(req: BulkQuoteRequest) -> BulkQuoteResponse:
    """代理店/クラブ一括契約のボリュームディスカウント見積（認証不要・公開）。"""
    try:
        q = bulk_contract.quote(req.tier, req.seats, via_agency=req.via_agency)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return BulkQuoteResponse(**vars(q))


@router.get("/subscription", response_model=SubscriptionResponse, summary="現在の契約状況")
def get_subscription(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionResponse:
    qs = billing_service.quota_status(db, current_user)
    sub = billing_service.get_or_create_subscription(db, current_user)
    return SubscriptionResponse(
        plan_tier=sub.plan_tier,
        plan_name=qs.plan.name,
        status=sub.status.value,
        billing_type=sub.billing_type.value,
        analyses_used=qs.analyses_used,
        monthly_analyses=qs.plan.monthly_analyses,
        analyses_remaining=qs.analyses_remaining,
        max_athletes=qs.plan.max_athletes,
    )


def _parse_tier(tier: str) -> PlanTier:
    try:
        return PlanTier(tier)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不正なプラン: {tier}",
        )


@router.post("/checkout", response_model=CheckoutResponse, summary="カード決済を開始する")
def checkout(
    req: CheckoutRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CheckoutResponse:
    tier = _parse_tier(req.tier)
    if tier == PlanTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Free プランに決済は不要です",
        )
    result = billing_service.start_checkout(db, current_user, tier, req.success_url, req.cancel_url)
    return CheckoutResponse(
        checkout_url=result.checkout_url, mode=result.mode, message=result.message
    )


@router.post(
    "/invoice",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="請求書払い(B2B)を申し込む",
)
def request_invoice(
    req: InvoiceRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionResponse:
    tier = _parse_tier(req.tier)
    if tier in (PlanTier.FREE, PlanTier.STARTER):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="請求書払いは Pro / Enterprise のみ対応です",
        )
    billing_service.request_invoice_billing(db, current_user, tier)
    qs = billing_service.quota_status(db, current_user)
    sub = billing_service.get_or_create_subscription(db, current_user)
    return SubscriptionResponse(
        plan_tier=sub.plan_tier,
        plan_name=qs.plan.name,
        status=sub.status.value,
        billing_type=sub.billing_type.value,
        analyses_used=qs.analyses_used,
        monthly_analyses=qs.plan.monthly_analyses,
        analyses_remaining=qs.analyses_remaining,
        max_athletes=qs.plan.max_athletes,
    )


@router.post("/webhook", summary="Stripe Webhook を受信する")
async def stripe_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Stripe からの Webhook。署名検証は本番で STRIPE_WEBHOOK_SECRET を用いる。"""
    try:
        event = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不正なペイロード")
    result = billing_service.handle_stripe_webhook(db, event)
    return {"result": result}
