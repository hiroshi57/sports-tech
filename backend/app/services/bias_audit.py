"""バイアス監査(外販 A#5)。

年代・体格などのセグメント別に総合スコアの分布を集計し、
セグメント間の不均衡（＝AIスコアの潜在バイアス）を検出する。

外部顧客・監査(A#10)向けに「特定属性が不当に高く/低く出ていないか」を
定量的に示す。公平性の説明責任(協会・自治体・教育現場)に直結する。

注意:
- 性別は現行データモデルに無いため本監査では扱わない（将来追加時に拡張）。
- サンプル数が小さいセグメントは統計的に不安定なため low_sample フラグを立てる。
- スコアは参考値。本監査はモデル改善・説明のための材料であり断定ではない。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.athlete import AthleteProfile
from app.models.user import User
from app.models.video import AnalysisResult, Video

# セグメント定義
_AGE_BANDS: list[tuple[str, int, int]] = [
    ("U12", 0, 12),
    ("U15", 13, 15),
    ("U18", 16, 18),
    ("U23", 19, 23),
    ("24+", 24, 200),
]

_BMI_BANDS: list[tuple[str, float, float]] = [
    ("痩せ型(BMI<18.5)", 0.0, 18.5),
    ("標準(18.5-25)", 18.5, 25.0),
    ("がっしり(25+)", 25.0, 999.0),
]

# 全体平均からの乖離がこの点数を超えるセグメントを disparity として警告
_DISPARITY_THRESHOLD = 5.0
_LOW_SAMPLE = 5


@dataclass(frozen=True)
class SegmentStat:
    segment: str
    sample_size: int
    mean_total: float
    delta_from_overall: float  # 全体平均との差（正=高く出ている）
    low_sample: bool
    flagged: bool  # |delta| が閾値超で要注意


@dataclass(frozen=True)
class BiasAuditReport:
    overall_mean: float
    overall_sample: int
    by_age: list[SegmentStat] = field(default_factory=list)
    by_build: list[SegmentStat] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _age_from_birth(birth: date | None, today: date | None = None) -> int | None:
    if birth is None:
        return None
    today = today or date.today()
    y = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        y -= 1
    return y


def _age_band(age: int | None) -> str | None:
    if age is None:
        return None
    for label, lo, hi in _AGE_BANDS:
        if lo <= age <= hi:
            return label
    return None


def _bmi_band(height_cm: float | None, weight_kg: float | None) -> str | None:
    if not height_cm or not weight_kg:
        return None
    h = height_cm / 100.0
    bmi = weight_kg / (h * h)
    for label, lo, hi in _BMI_BANDS:
        if lo <= bmi < hi:
            return label
    return None


def _segment_stats(
    groups: dict[str, list[float]],
    overall_mean: float,
) -> list[SegmentStat]:
    stats: list[SegmentStat] = []
    for seg, vals in groups.items():
        n = len(vals)
        mean = round(sum(vals) / n, 1) if n else 0.0
        delta = round(mean - overall_mean, 1)
        stats.append(
            SegmentStat(
                segment=seg,
                sample_size=n,
                mean_total=mean,
                delta_from_overall=delta,
                low_sample=n < _LOW_SAMPLE,
                flagged=(abs(delta) >= _DISPARITY_THRESHOLD and n >= _LOW_SAMPLE),
            )
        )
    # サンプル多い順に並べる
    return sorted(stats, key=lambda s: s.sample_size, reverse=True)


def run_audit(db: Session, today: date | None = None) -> BiasAuditReport:
    """全 AnalysisResult を対象にセグメント別の総合スコアを監査する。"""
    rows = db.execute(
        select(
            AnalysisResult.total_score,
            User.birth_date,
            AthleteProfile.height_cm,
            AthleteProfile.weight_kg,
        )
        .join(Video, Video.id == AnalysisResult.video_id)
        .join(AthleteProfile, AthleteProfile.id == Video.athlete_id)
        .join(User, User.id == AthleteProfile.user_id)
    ).all()

    totals = [float(r[0]) for r in rows]
    overall_sample = len(totals)
    overall_mean = round(sum(totals) / overall_sample, 1) if overall_sample else 0.0

    age_groups: dict[str, list[float]] = {}
    build_groups: dict[str, list[float]] = {}
    for total, birth, h, w in rows:
        ab = _age_band(_age_from_birth(birth, today))
        if ab:
            age_groups.setdefault(ab, []).append(float(total))
        bb = _bmi_band(h, w)
        if bb:
            build_groups.setdefault(bb, []).append(float(total))

    notes: list[str] = []
    if overall_sample < _LOW_SAMPLE:
        notes.append("全体サンプルが少なく、結果は統計的に不安定です。")
    age_stats = _segment_stats(age_groups, overall_mean)
    build_stats = _segment_stats(build_groups, overall_mean)
    flagged = [s.segment for s in age_stats + build_stats if s.flagged]
    if flagged:
        notes.append(f"全体平均から±{_DISPARITY_THRESHOLD}点以上乖離: {', '.join(flagged)}")
    else:
        notes.append("閾値を超える顕著なセグメント間バイアスは検出されませんでした。")
    notes.append("性別は現行データに無いため未評価。スコアは参考値です。")

    return BiasAuditReport(
        overall_mean=overall_mean,
        overall_sample=overall_sample,
        by_age=age_stats,
        by_build=build_stats,
        notes=notes,
    )
