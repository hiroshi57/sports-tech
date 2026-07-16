"""課金・サブスクリプション サービス(外販 E#37 / E#38)。

責務:
- サブスクリプションの取得/作成（未契約は FREE 相当を自動生成）
- フリーミアムのクォータ判定（分析本数・選手数）と当期利用カウント(E#38)
- Stripe 連携（Checkout 作成 / Webhook 反映）。Stripe SDK 未導入・鍵未設定でも
  動く manual(請求書払い) フォールバックを持つ(E#37)

Stripe SDK はオプション依存。`import stripe` が失敗、または STRIPE_SECRET_KEY が
未設定の場合は manual モードで動作し、請求書払いフローに誘導する。
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.athlete import AthleteProfile
from app.models.subscription import BillingType, Subscription, SubscriptionStatus
from app.models.user import User
from app.services import billing_plans
from app.services.billing_plans import Feature, Plan, PlanTier


class QuotaExceededError(Exception):
    """当期のクォータ超過（分析本数・選手数）。"""

    def __init__(self, message: str, *, limit: int, used: int) -> None:
        super().__init__(message)
        self.message = message
        self.limit = limit
        self.used = used


def _stripe_enabled() -> bool:
    """Stripe SDK が使え、かつ秘密鍵が設定されているか。"""
    if not os.getenv("STRIPE_SECRET_KEY"):
        return False
    try:
        import stripe  # noqa: F401
    except ImportError:
        return False
    return True


def _current_period_start(now: datetime | None = None) -> datetime:
    """当月の開始時刻（UTC, 月初 00:00）。"""
    now = now or datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_or_create_subscription(db: Session, user: User) -> Subscription:
    """ユーザーのサブスクリプションを取得（無ければ FREE で作成）。"""
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).one_or_none()
    if sub is None:
        sub = Subscription(
            id=uuid.uuid4(),
            user_id=user.id,
            plan_tier=billing_plans.DEFAULT_TIER.value,
            status=SubscriptionStatus.ACTIVE,
            billing_type=BillingType.CARD,
            period_start=_current_period_start(),
            analyses_used=0,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def _reset_if_new_period(db: Session, sub: Subscription, now: datetime | None = None) -> None:
    """期が変わっていたら当期利用量をリセットする。"""
    start = _current_period_start(now)
    period_start = sub.period_start
    if period_start is not None and period_start.tzinfo is None:
        # SQLite など naive datetime を返すバックエンドに対応
        period_start = period_start.replace(tzinfo=UTC)
    if period_start is None or period_start < start:
        sub.period_start = start
        sub.analyses_used = 0
        db.add(sub)
        db.commit()
        db.refresh(sub)


def plan_for(sub: Subscription) -> Plan:
    return billing_plans.get_plan(sub.plan_tier)


@dataclass(frozen=True)
class QuotaStatus:
    plan: Plan
    analyses_used: int
    analyses_remaining: int | None  # None=無制限


def quota_status(db: Session, user: User) -> QuotaStatus:
    """当期の利用状況を返す（期跨ぎリセット込み）。"""
    sub = get_or_create_subscription(db, user)
    _reset_if_new_period(db, sub)
    plan = plan_for(sub)
    if plan.monthly_analyses is None:
        remaining = None
    else:
        remaining = max(0, plan.monthly_analyses - sub.analyses_used)
    return QuotaStatus(plan=plan, analyses_used=sub.analyses_used, analyses_remaining=remaining)


def check_can_analyze(db: Session, user: User) -> None:
    """分析実行が許可されるか判定。超過時は QuotaExceededError(E#38)。

    - 無制限プランは常に許可
    - overage を許すプランは超過しても許可（従量課金）
    - FREE のように overage 不可のプランは基本枠でストップ（PROへの転換点）
    """
    sub = get_or_create_subscription(db, user)
    _reset_if_new_period(db, sub)
    plan = plan_for(sub)
    if plan.monthly_analyses is None:
        return
    if sub.analyses_used < plan.monthly_analyses:
        return
    if plan.allows_overage():
        return
    raise QuotaExceededError(
        f"{plan.name} プランの当月分析枠（{plan.monthly_analyses}本）を使い切りました。"
        "上位プランへのアップグレードで継続できます。",
        limit=plan.monthly_analyses,
        used=sub.analyses_used,
    )


def record_analysis(db: Session, user: User) -> int:
    """分析1本の利用を記録し、当期の累計を返す。"""
    sub = get_or_create_subscription(db, user)
    _reset_if_new_period(db, sub)
    sub.analyses_used += 1
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub.analyses_used


def check_can_add_athlete(db: Session, user: User) -> None:
    """選手を追加できるか（選手数クォータ, E#38）。超過時は QuotaExceededError。"""
    sub = get_or_create_subscription(db, user)
    plan = plan_for(sub)
    if plan.max_athletes is None:
        return
    count = db.query(AthleteProfile).filter(AthleteProfile.user_id == user.id).count()
    if count >= plan.max_athletes:
        raise QuotaExceededError(
            f"{plan.name} プランの選手登録上限（{plan.max_athletes}人）に達しています。",
            limit=plan.max_athletes,
            used=count,
        )


def has_feature(db: Session, user: User, feature: Feature) -> bool:
    """契約プランが指定機能を含むか(E#38 機能ゲート)。"""
    sub = get_or_create_subscription(db, user)
    return plan_for(sub).has_feature(feature)


# ── 決済フロー(E#37) ──────────────────────────────────────────────


@dataclass(frozen=True)
class CheckoutResult:
    checkout_url: str | None
    mode: str  # "stripe" | "manual"
    message: str


def start_checkout(
    db: Session,
    user: User,
    tier: PlanTier | str,
    success_url: str,
    cancel_url: str,
) -> CheckoutResult:
    """カード決済のチェックアウトを開始する。

    Stripe が有効なら Checkout Session を作り URL を返す。
    未設定/未導入なら manual モードを返し、請求書払いフローへ誘導する。
    """
    plan = billing_plans.get_plan(tier)
    if plan.monthly_price_jpy is None:
        return CheckoutResult(
            checkout_url=None,
            mode="manual",
            message="Enterprise は個別見積です。請求書払い(お問い合わせ)からお申込みください。",
        )

    if not _stripe_enabled():
        return CheckoutResult(
            checkout_url=None,
            mode="manual",
            message="オンライン決済は準備中です。請求書払いでのお申込みを承ります。",
        )

    import stripe

    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    sub = get_or_create_subscription(db, user)
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=sub.stripe_customer_id or None,
        client_reference_id=str(user.id),
        line_items=[
            {
                "price_data": {
                    "currency": "jpy",
                    "product_data": {"name": f"sports-tech {plan.name}"},
                    "unit_amount": plan.monthly_price_jpy,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }
        ],
        metadata={"tier": plan.tier.value, "user_id": str(user.id)},
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return CheckoutResult(
        checkout_url=session.url, mode="stripe", message="決済ページへ遷移します。"
    )


def apply_subscription_active(
    db: Session,
    user_id: uuid.UUID,
    tier: PlanTier | str,
    *,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    billing_type: BillingType = BillingType.CARD,
) -> Subscription:
    """決済成立/請求承認時にプランを有効化する（Webhook・管理操作から呼ぶ）。"""
    tier_value = tier.value if isinstance(tier, PlanTier) else PlanTier(tier).value
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).one_or_none()
    if sub is None:
        sub = Subscription(id=uuid.uuid4(), user_id=user_id)
        db.add(sub)
    sub.plan_tier = tier_value
    sub.status = SubscriptionStatus.ACTIVE
    sub.billing_type = billing_type
    if stripe_customer_id:
        sub.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        sub.stripe_subscription_id = stripe_subscription_id
    if sub.period_start is None:
        sub.period_start = _current_period_start()
    db.commit()
    db.refresh(sub)
    return sub


def handle_stripe_webhook(db: Session, event: dict) -> str:
    """Stripe Webhook イベントを反映する。

    対応:
    - checkout.session.completed → プラン有効化
    - customer.subscription.deleted → CANCELED
    戻り値は処理内容の要約（未対応イベントは "ignored"）。
    """
    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        user_id_raw = (obj.get("metadata") or {}).get("user_id") or obj.get("client_reference_id")
        tier = (obj.get("metadata") or {}).get("tier", PlanTier.PRO.value)
        if not user_id_raw:
            return "ignored: no user_id"
        apply_subscription_active(
            db,
            uuid.UUID(user_id_raw),
            tier,
            stripe_customer_id=obj.get("customer"),
            stripe_subscription_id=obj.get("subscription"),
            billing_type=BillingType.CARD,
        )
        return f"activated:{tier}"

    if etype == "customer.subscription.deleted":
        stripe_sub_id = obj.get("id")
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub_id)
            .one_or_none()
        )
        if sub is None:
            return "ignored: unknown subscription"
        sub.status = SubscriptionStatus.CANCELED
        sub.plan_tier = billing_plans.DEFAULT_TIER.value
        db.commit()
        return "canceled"

    return "ignored"


def request_invoice_billing(
    db: Session,
    user: User,
    tier: PlanTier | str,
) -> Subscription:
    """請求書払い(B2B)の申込を受け付け、TRIALING(承認待ち)で登録する(E#37)。

    実運用では別途与信・請求書発行の承認フローが入る。ここでは請求書払い契約を
    作成し status=TRIALING（利用開始・請求は月末締め）で有効化する。
    """
    return _apply_invoice(db, user.id, tier)


def _apply_invoice(db: Session, user_id: uuid.UUID, tier: PlanTier | str) -> Subscription:
    tier_value = tier.value if isinstance(tier, PlanTier) else PlanTier(tier).value
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).one_or_none()
    if sub is None:
        sub = Subscription(id=uuid.uuid4(), user_id=user_id)
        db.add(sub)
    sub.plan_tier = tier_value
    sub.status = SubscriptionStatus.TRIALING
    sub.billing_type = BillingType.INVOICE
    if sub.period_start is None:
        sub.period_start = _current_period_start()
    db.commit()
    db.refresh(sub)
    return sub
