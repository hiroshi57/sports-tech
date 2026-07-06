"""セルフケアサービス(#13/#14) — 怪我リスク推定・記録管理。

怪我リスクは以下から推定する（Phase 1 ヒューリスティック / 医療診断ではない）:
1. ACWR（急性:慢性 負荷比）— 直近7日の負荷 / 過去28日の平均週負荷
   スポーツ医学で 1.5 超は怪我リスク増とされる（"sweet spot" は 0.8〜1.3）
2. 直近の平均疲労度（fatigue_level 4〜5 が続くと高リスク）
3. 睡眠不足（直近の平均睡眠 < 6h で加点）

いずれも参考値。精度検証は外販ロードマップ #21 系で行う。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import ActivityLog, SelfCareRecord
from app.models.athlete import AthleteProfile
from app.models.user import User
from app.schemas.selfcare import SelfCareRecordCreate

# ACWR のリスク閾値（スポーツ医学の一般的な目安）
ACWR_HIGH_RISK = 1.5
ACWR_SWEET_SPOT_LOW = 0.8

# 疲労・睡眠の閾値
HIGH_FATIGUE_THRESHOLD = 4.0
LOW_SLEEP_THRESHOLD = 6.0

ACUTE_WINDOW_DAYS = 7
CHRONIC_WINDOW_DAYS = 28


@dataclass(frozen=True)
class InjuryRisk:
    risk_score: float
    risk_level: str
    factors: list[str] = field(default_factory=list)
    acwr: float | None = None


def _get_profile(db: Session, user: User) -> AthleteProfile:
    profile = db.execute(
        select(AthleteProfile).where(AthleteProfile.user_id == user.id)
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="選手プロフィールが未登録です。",
        )
    return profile


def create_record(db: Session, user: User, req: SelfCareRecordCreate) -> SelfCareRecord:
    """セルフケア記録を作成し、怪我リスクを計算して保存する。"""
    profile = _get_profile(db, user)
    record = SelfCareRecord(
        id=uuid.uuid4(),
        athlete_id=profile.id,
        record_date=req.record_date,
        sleep_hours=req.sleep_hours,
        weight_kg=req.weight_kg,
        nutrition_notes=req.nutrition_notes,
    )
    # 記録時点の怪我リスクをスナップショットとして保存
    risk = _compute_risk(db, profile.id, as_of=req.record_date)
    record.injury_risk_score = risk.risk_score
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_records(db: Session, user: User, limit: int = 50, offset: int = 0) -> list[SelfCareRecord]:
    """自分のセルフケア記録一覧を取得する（新しい順）。"""
    profile = _get_profile(db, user)
    stmt = (
        select(SelfCareRecord)
        .where(SelfCareRecord.athlete_id == profile.id)
        .order_by(SelfCareRecord.record_date.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all())


def get_injury_risk(db: Session, user: User, as_of: date | None = None) -> InjuryRisk:
    """現在の怪我リスクを推定する。"""
    profile = _get_profile(db, user)
    return _compute_risk(db, profile.id, as_of=as_of or date.today())


def _compute_risk(db: Session, athlete_id: uuid.UUID, *, as_of: date) -> InjuryRisk:
    """活動記録・セルフケア記録から怪我リスク（0〜100）を推定する。"""
    acute_start = as_of - timedelta(days=ACUTE_WINDOW_DAYS)
    chronic_start = as_of - timedelta(days=CHRONIC_WINDOW_DAYS)

    logs = list(
        db.execute(
            select(ActivityLog)
            .where(ActivityLog.athlete_id == athlete_id)
            .where(ActivityLog.activity_date > chronic_start)
            .where(ActivityLog.activity_date <= as_of)
        ).scalars()
    )

    factors: list[str] = []
    score = 0.0

    # ── ACWR（急性:慢性 負荷比）──────────────────────────────────
    acute_load = sum(x.duration_min for x in logs if x.activity_date > acute_start)
    chronic_total = sum(x.duration_min for x in logs)
    # 慢性負荷を「週あたり平均」に換算（28日 → 4週）
    chronic_weekly = chronic_total / (CHRONIC_WINDOW_DAYS / 7)

    acwr: float | None = None
    if chronic_weekly > 0:
        acwr = round(acute_load / chronic_weekly, 2)
        if acwr > ACWR_HIGH_RISK:
            score += 45
            factors.append(f"直近の負荷が急増しています（ACWR={acwr}、1.5超は要注意）")
        elif acwr < ACWR_SWEET_SPOT_LOW:
            score += 10
            factors.append(f"負荷が低下しています（ACWR={acwr}）")

    # ── 疲労度 ────────────────────────────────────────────────
    recent_fatigue = [x.fatigue_level for x in logs if x.activity_date > acute_start]
    if recent_fatigue:
        avg_fatigue = sum(recent_fatigue) / len(recent_fatigue)
        if avg_fatigue >= HIGH_FATIGUE_THRESHOLD:
            score += 35
            factors.append(f"直近の疲労度が高い状態が続いています（平均{avg_fatigue:.1f}/5）")
        elif avg_fatigue >= 3.0:
            score += 15

    # ── 睡眠 ──────────────────────────────────────────────────
    sleep_records = list(
        db.execute(
            select(SelfCareRecord)
            .where(SelfCareRecord.athlete_id == athlete_id)
            .where(SelfCareRecord.record_date > acute_start)
            .where(SelfCareRecord.record_date <= as_of)
        ).scalars()
    )
    sleeps = [r.sleep_hours for r in sleep_records if r.sleep_hours is not None]
    if sleeps:
        avg_sleep = sum(sleeps) / len(sleeps)
        if avg_sleep < LOW_SLEEP_THRESHOLD:
            score += 20
            factors.append(f"睡眠時間が不足しています（平均{avg_sleep:.1f}時間）")

    score = min(100.0, score)
    if not factors:
        factors.append("特に大きなリスク要因は検出されていません")

    if score >= 60:
        level = "high"
    elif score >= 30:
        level = "moderate"
    else:
        level = "low"

    return InjuryRisk(risk_score=round(score, 1), risk_level=level, factors=factors, acwr=acwr)
