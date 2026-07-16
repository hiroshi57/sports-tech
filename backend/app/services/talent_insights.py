"""タレントインサイト(外販 C#28 類似選手 / C#29 市場価値推定)。

- C#28: 4基礎スコアのベクトル類似度（コサイン類似度）で似た公開選手を返す。
  Phase 1 はスコア4次元。pgvector 導入時に高次元埋め込みへ拡張する。
- C#29: 総合スコア・年齢・ポジションから移籍市場価値の参考レンジを推定する。
  実取引データが無いため係数はヒューリスティック。参考値として明示する。
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.athlete import AthleteProfile
from app.models.user import User
from app.models.video import AnalysisResult, Video

_METRICS = (
    "sprint_score",
    "ball_control_score",
    "positioning_score",
    "body_usage_score",
)


# ── C#28: 類似選手レコメンド ──────────────────────────────────────


@dataclass(frozen=True)
class SimilarAthlete:
    athlete_id: uuid.UUID
    name: str
    position: str | None
    similarity: float  # 0-100
    total_score: float


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _latest_scores_by_profile(db: Session) -> list[tuple[AthleteProfile, AnalysisResult]]:
    """公開選手ごとの最新分析結果を返す。"""
    rows = db.execute(
        select(AthleteProfile, AnalysisResult)
        .join(Video, Video.athlete_id == AthleteProfile.id)
        .join(AnalysisResult, AnalysisResult.video_id == Video.id)
        .where(AthleteProfile.is_public.is_(True))
        .order_by(AthleteProfile.id, AnalysisResult.created_at.desc())
    ).all()
    latest: dict[uuid.UUID, tuple[AthleteProfile, AnalysisResult]] = {}
    for profile, result in rows:
        if profile.id not in latest:
            latest[profile.id] = (profile, result)
    return list(latest.values())


def find_similar(
    db: Session,
    target_profile: AthleteProfile,
    target_result: AnalysisResult,
    *,
    limit: int = 5,
    same_position_only: bool = False,
) -> list[SimilarAthlete]:
    """C#28: スコアベクトルが近い公開選手を類似度順に返す。"""
    target_vec = [float(getattr(target_result, m)) for m in _METRICS]
    out: list[SimilarAthlete] = []
    for profile, result in _latest_scores_by_profile(db):
        if profile.id == target_profile.id:
            continue
        if same_position_only and profile.position != target_profile.position:
            continue
        vec = [float(getattr(result, m)) for m in _METRICS]
        # コサイン類似度は高スコア帯で飽和しやすいので距離も加味
        cos = _cosine(target_vec, vec)
        dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(target_vec, vec, strict=True)))
        # 距離0で100点、距離50以上で0点に線形減衰し、コサインと平均
        dist_score = max(0.0, 1.0 - dist / 50.0)
        similarity = round(((cos + dist_score) / 2.0) * 100, 1)
        out.append(
            SimilarAthlete(
                athlete_id=profile.id,
                name=profile.name,
                position=profile.position,
                similarity=similarity,
                total_score=result.total_score,
            )
        )
    out.sort(key=lambda s: s.similarity, reverse=True)
    return out[:limit]


# ── C#29: 市場価値推定 ────────────────────────────────────────────

# ポジション係数（市場ではFW/攻撃的人材にプレミアが付きやすい）
_POSITION_FACTOR: dict[str, float] = {"FW": 1.2, "MF": 1.1, "DF": 1.0, "GK": 0.9}


# 年齢係数（若いほど将来価値でプレミア）
def _age_factor(age: int | None) -> float:
    if age is None:
        return 1.0
    if age <= 15:
        return 1.3
    if age <= 18:
        return 1.25
    if age <= 21:
        return 1.15
    if age <= 24:
        return 1.0
    return max(0.5, 1.0 - (age - 24) * 0.05)


@dataclass(frozen=True)
class MarketValueEstimate:
    low_jpy: int  # レンジ下限
    high_jpy: int  # レンジ上限
    age_factor: float
    position_factor: float
    comment: str


def _age_from_birth(birth: date | None, today: date | None = None) -> int | None:
    if birth is None:
        return None
    today = today or date.today()
    y = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        y -= 1
    return y


def estimate_market_value(
    total_score: float,
    position: str | None,
    birth_date: date | None,
) -> MarketValueEstimate:
    """C#29: 移籍市場価値の参考レンジ(円)を推定する。

    base = (total/100)^2 × 1,000万円 を基礎とし、年齢・ポジションで補正。
    実取引データが無い Phase 1 の参考モデル。契約判断の根拠には使わないこと。
    """
    ratio = max(0.0, min(1.0, total_score / 100.0))
    base = (ratio**2) * 10_000_000  # スコアに対して逓増
    af = _age_factor(_age_from_birth(birth_date))
    pf = _POSITION_FACTOR.get((position or "").upper(), 1.0)
    mid = base * af * pf
    low = int(round(mid * 0.6, -4))  # 1万円単位に丸め
    high = int(round(mid * 1.5, -4))
    comment = (
        "スコア・年齢・ポジションからの参考レンジ。実績・出場歴・市場動向は"
        "未反映のため、交渉・契約の根拠には使用しないこと。"
    )
    return MarketValueEstimate(
        low_jpy=low, high_jpy=high, age_factor=af, position_factor=pf, comment=comment
    )


def estimate_for_profile(
    db: Session,
    profile: AthleteProfile,
    result: AnalysisResult,
) -> MarketValueEstimate:
    """プロフィール＋最新結果から市場価値レンジを推定する。"""
    owner = db.get(User, profile.user_id)
    return estimate_market_value(
        result.total_score,
        profile.position,
        owner.birth_date if owner else None,
    )
