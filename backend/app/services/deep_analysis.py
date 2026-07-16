"""深掘り分析サービス(外販 B#11-17, B#19)。

実データ（AnalysisResult の4基礎スコア＋履歴）から、スカウトが実際に見る
詳細観点を導出する。Web デモ側の擬似値を廃し、バックエンドを単一の算出源とする。

含まれる分析:
- B#11: 14項目の詳細能力（4基礎スコアからの導出）
- B#12: 対人プレー（1対1攻守）
- B#13: 利き足/両足の技術バランス
- B#14: 試合状況別評価（攻撃/守備/トランジション）
- B#15: ゾーン占有ヒートマップ（ポジション＋スコアからの推定）
- B#16: 判断スピード（準備動作・認知）
- B#17: セットプレー・空中戦
- B#19: 疲労耐性カーブ（時間帯別パフォーマンス維持率）

Phase 1 ヒューリスティック: 現段階では姿勢推定の生データ（関節座標・イベント
タグ）が保存されていないため、4基礎スコア・履歴・体格から決定論的に導出する。
実測パイプライン(トラッキング・イベント検出)導入時に本モジュールの各関数を
実測値へ差し替える設計（インターフェースは維持）。

スコアはすべて参考値（is_reference_score: true）。
"""

from __future__ import annotations

from dataclasses import dataclass

# 4基礎スコアのキー
_SPRINT = "sprint_score"
_BALL = "ball_control_score"
_POS = "positioning_score"
_BODY = "body_usage_score"


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return round(max(lo, min(hi, v)), 1)


def _mix(scores: dict[str, float], weights: dict[str, float], bias: float = 0.0) -> float:
    """基礎スコアの加重合成（重みは合計1.0を想定）。"""
    total = sum(scores[k] * w for k, w in weights.items())
    return _clamp(total + bias)


# ── B#11: 14項目の詳細能力 ────────────────────────────────────────

# 各詳細能力を4基礎スコアの加重で定義（重み合計=1.0）
_ABILITY_DEFS: list[tuple[str, dict[str, float], float]] = [
    ("スピード", {_SPRINT: 0.8, _BODY: 0.2}, 0.0),
    ("加速力", {_SPRINT: 0.7, _BODY: 0.3}, -2.0),
    ("敏捷性", {_SPRINT: 0.4, _BODY: 0.4, _BALL: 0.2}, 0.0),
    ("ドリブル", {_BALL: 0.7, _SPRINT: 0.2, _BODY: 0.1}, 0.0),
    ("ファーストタッチ", {_BALL: 0.8, _POS: 0.2}, -1.0),
    ("パス精度", {_BALL: 0.6, _POS: 0.4}, 0.0),
    ("シュート", {_BALL: 0.5, _BODY: 0.3, _POS: 0.2}, -3.0),
    ("ポジショニング", {_POS: 0.9, _BALL: 0.1}, 0.0),
    ("視野・スキャン", {_POS: 0.7, _BALL: 0.3}, -2.0),
    ("守備対応", {_POS: 0.5, _BODY: 0.4, _SPRINT: 0.1}, -1.0),
    ("フィジカル強度", {_BODY: 0.8, _SPRINT: 0.2}, 0.0),
    ("バランス", {_BODY: 0.7, _BALL: 0.3}, 0.0),
    ("スタミナ", {_SPRINT: 0.5, _BODY: 0.5}, -2.0),
    ("空中戦", {_BODY: 0.6, _POS: 0.4}, -4.0),
]


@dataclass(frozen=True)
class AbilityItem:
    name: str
    value: float
    basis: str  # 導出根拠（主要な基礎スコア）


def compute_abilities(scores: dict[str, float]) -> list[AbilityItem]:
    """B#11: 4基礎スコアから14項目の詳細能力を導出する。"""
    items: list[AbilityItem] = []
    label = {
        _SPRINT: "スプリント",
        _BALL: "ボールコントロール",
        _POS: "ポジショニング",
        _BODY: "身体の使い方",
    }
    for name, weights, bias in _ABILITY_DEFS:
        top = max(weights, key=lambda k: weights[k])
        items.append(
            AbilityItem(
                name=name,
                value=_mix(scores, weights, bias),
                basis=f"{label[top]}を主成分に導出",
            )
        )
    return items


# ── B#12: 対人プレー ──────────────────────────────────────────────


@dataclass(frozen=True)
class DuelAnalysis:
    attacking_1v1: float  # 1対1仕掛け（攻撃）
    defending_1v1: float  # 1対1対応（守備）
    pressing: float  # 寄せの速さ・強度
    comment: str


def compute_duel(scores: dict[str, float]) -> DuelAnalysis:
    """B#12: 対人プレー（1対1攻守・寄せ）を導出する。"""
    atk = _mix(scores, {_BALL: 0.5, _SPRINT: 0.3, _BODY: 0.2})
    dfd = _mix(scores, {_POS: 0.4, _BODY: 0.4, _SPRINT: 0.2})
    prs = _mix(scores, {_SPRINT: 0.5, _POS: 0.3, _BODY: 0.2}, -1.0)
    if atk >= dfd + 10:
        comment = "仕掛け優位型。攻撃の1対1で違いを作れる。"
    elif dfd >= atk + 10:
        comment = "対人守備型。1対1の対応と寄せに強みがある。"
    else:
        comment = "攻守バランス型。局面を選ばず1対1で戦える。"
    return DuelAnalysis(attacking_1v1=atk, defending_1v1=dfd, pressing=prs, comment=comment)


# ── B#13: 利き足/両足バランス ─────────────────────────────────────


@dataclass(frozen=True)
class FootednessAnalysis:
    dominant_foot_skill: float  # 利き足の技術
    weak_foot_skill: float  # 逆足の技術
    balance_pct: float  # 両足バランス(逆足/利き足×100)
    comment: str


def compute_footedness(scores: dict[str, float]) -> FootednessAnalysis:
    """B#13: 利き足/逆足の技術差を導出する。

    Phase 1: ボールコントロールと身体の使い方の乖離から逆足依存度を推定。
    実測では左右足別のタッチイベントから算出する。
    """
    ball = scores[_BALL]
    body = scores[_BODY]
    dominant = _clamp(ball + 2.0)
    # 身体操作がボール技術より低いほど逆足が弱い傾向と仮定
    gap = max(0.0, ball - body)
    weak = _clamp(ball - 8.0 - gap * 0.5)
    balance = _clamp((weak / dominant) * 100 if dominant else 0.0)
    if balance >= 85:
        comment = "両足遜色なし。逆足でもプレー選択を狭めない。"
    elif balance >= 70:
        comment = "逆足も実用レベル。仕上げの精度向上で幅が広がる。"
    else:
        comment = "利き足依存が強め。逆足のファーストタッチ強化を推奨。"
    return FootednessAnalysis(
        dominant_foot_skill=dominant,
        weak_foot_skill=weak,
        balance_pct=balance,
        comment=comment,
    )


# ── B#14: 試合状況別評価 ──────────────────────────────────────────


@dataclass(frozen=True)
class SituationalAnalysis:
    attacking: float  # 攻撃局面
    defending: float  # 守備局面
    transition: float  # トランジション（切替）
    comment: str


def compute_situational(scores: dict[str, float]) -> SituationalAnalysis:
    """B#14: 攻撃/守備/トランジションの局面別評価。"""
    atk = _mix(scores, {_BALL: 0.5, _POS: 0.3, _SPRINT: 0.2})
    dfd = _mix(scores, {_POS: 0.5, _BODY: 0.3, _SPRINT: 0.2})
    trn = _mix(scores, {_SPRINT: 0.5, _POS: 0.3, _BALL: 0.2})
    best = max((atk, "攻撃"), (dfd, "守備"), (trn, "トランジション"))
    return SituationalAnalysis(
        attacking=atk,
        defending=dfd,
        transition=trn,
        comment=f"最も強みが出るのは{best[1]}局面（{best[0]}）。",
    )


# ── B#15: ゾーン占有ヒートマップ ──────────────────────────────────

# ポジション別の基準ゾーン占有率（3x3グリッド: 自陣/中盤/敵陣 × 左/中/右）
_ZONE_BASE: dict[str, list[list[float]]] = {
    # rows: 自陣→中盤→敵陣, cols: 左/中央/右（%目安）
    "FW": [[2, 3, 2], [8, 12, 8], [18, 29, 18]],
    "MF": [[5, 8, 5], [15, 24, 15], [8, 12, 8]],
    "DF": [[16, 26, 16], [10, 16, 10], [2, 2, 2]],
    "GK": [[10, 78, 10], [0, 2, 0], [0, 0, 0]],
}
_ZONE_DEFAULT: list[list[float]] = [[8, 10, 8], [12, 20, 12], [10, 12, 8]]


@dataclass(frozen=True)
class HeatmapAnalysis:
    zones: list[list[float]]  # 3x3 占有率(%) 自陣→敵陣 × 左/中/右
    coverage: float  # 行動範囲の広さ(0-100)
    comment: str


def compute_heatmap(position: str | None, scores: dict[str, float]) -> HeatmapAnalysis:
    """B#15: ポジションとスプリント力からゾーン占有を推定する。

    Phase 1: 実トラッキング座標が無いため、ポジション基準分布を
    スプリント/ポジショニングで補正した推定値。実測導入時に置換する。
    """
    base = _ZONE_BASE.get((position or "").upper(), _ZONE_DEFAULT)
    # スプリントが高いほど行動範囲が広がる（分布を平滑化）
    mobility = (scores[_SPRINT] + scores[_POS]) / 2.0
    spread = _clamp((mobility - 50.0) / 50.0, 0.0, 1.0) * 0.3  # 最大30%平滑化
    n_cells = 9
    flat_avg = 100.0 / n_cells
    zones = [[round(v * (1 - spread) + flat_avg * spread, 1) for v in row] for row in base]
    coverage = _clamp(40 + mobility * 0.6)
    return HeatmapAnalysis(
        zones=zones,
        coverage=coverage,
        comment=f"行動範囲スコア {coverage}。ポジション基準にスプリント補正した推定分布。",
    )


# ── B#16: 判断スピード ────────────────────────────────────────────


@dataclass(frozen=True)
class DecisionAnalysis:
    scan_frequency: float  # 首振り・周囲確認(推定)
    decision_speed: float  # 判断の速さ
    pre_receive_prep: float  # 受ける前の準備
    comment: str


def compute_decision(scores: dict[str, float]) -> DecisionAnalysis:
    """B#16: 判断スピード（認知・準備）を導出する。"""
    scan = _mix(scores, {_POS: 0.8, _BALL: 0.2}, -3.0)
    speed = _mix(scores, {_POS: 0.5, _BALL: 0.3, _SPRINT: 0.2}, -1.0)
    prep = _mix(scores, {_POS: 0.6, _BODY: 0.4}, -2.0)
    avg = (scan + speed + prep) / 3
    if avg >= 75:
        comment = "認知→判断→実行が速い。プレッシャー下でも選択肢を保てる。"
    elif avg >= 60:
        comment = "判断は平均以上。受ける前のスキャン頻度を上げると更に伸びる。"
    else:
        comment = "判断に改善余地。首振り・体の向きの習慣化を推奨。"
    return DecisionAnalysis(
        scan_frequency=scan,
        decision_speed=speed,
        pre_receive_prep=prep,
        comment=comment,
    )


# ── B#17: セットプレー・空中戦 ────────────────────────────────────


@dataclass(frozen=True)
class SetPieceAnalysis:
    aerial_duel: float  # 空中戦
    delivery: float  # プレースキック精度
    box_presence: float  # ボックス内での存在感
    comment: str


def compute_set_piece(
    scores: dict[str, float],
    height_cm: float | None,
) -> SetPieceAnalysis:
    """B#17: セットプレー・空中戦を導出する（身長補正あり）。"""
    height_bonus = 0.0
    if height_cm:
        height_bonus = _clamp((height_cm - 170.0) * 0.5, -8.0, 8.0)
    aerial = _clamp(_mix(scores, {_BODY: 0.6, _POS: 0.4}, -3.0) + height_bonus)
    delivery = _mix(scores, {_BALL: 0.8, _POS: 0.2}, -4.0)
    box = _clamp(_mix(scores, {_POS: 0.5, _BODY: 0.5}, -2.0) + height_bonus * 0.5)
    comment = (
        "空中戦に強み。セットプレーのターゲットになれる。"
        if aerial >= 70
        else "空中戦は平均圏。ポジショニングで補うタイプ。"
    )
    return SetPieceAnalysis(
        aerial_duel=aerial, delivery=delivery, box_presence=box, comment=comment
    )


# ── B#19: 疲労耐性カーブ ──────────────────────────────────────────


@dataclass(frozen=True)
class FatigueAnalysis:
    curve: list[float]  # 15分刻み(0-90分)のパフォーマンス維持率(%)
    endurance_index: float  # 終盤(75-90分)の維持率
    comment: str


def compute_fatigue(
    scores: dict[str, float],
    consistency: float | None,
) -> FatigueAnalysis:
    """B#19: 疲労時のパフォーマンス低下カーブを推定する。

    Phase 1: スタミナ要素（スプリント×身体）と履歴の安定性(consistency)から
    時間帯別の維持率を推定。実測では試合内セグメント別スコアで置換する。
    """
    stamina = (scores[_SPRINT] * 0.5 + scores[_BODY] * 0.5) / 100.0  # 0-1
    stability = (consistency if consistency is not None else 60.0) / 100.0
    # 低下率: スタミナ・安定性が高いほど緩やか（15分あたり最大4%低下）
    decay_per_seg = 4.0 * (1.0 - (stamina * 0.6 + stability * 0.4))
    curve = [round(max(60.0, 100.0 - decay_per_seg * i), 1) for i in range(6)]
    endurance = curve[-1]
    if endurance >= 90:
        comment = "終盤も出力が落ちにくい。フル出場に耐えるスタミナ。"
    elif endurance >= 80:
        comment = "標準的な持久力。70分以降の強度管理がポイント。"
    else:
        comment = "終盤の低下が大きめ。交代カードや持久系トレの検討を。"
    return FatigueAnalysis(curve=curve, endurance_index=endurance, comment=comment)


# ── 統合 ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DeepAnalysis:
    abilities: list[AbilityItem]
    duel: DuelAnalysis
    footedness: FootednessAnalysis
    situational: SituationalAnalysis
    heatmap: HeatmapAnalysis
    decision: DecisionAnalysis
    set_piece: SetPieceAnalysis
    fatigue: FatigueAnalysis


def analyze(
    *,
    sprint_score: float,
    ball_control_score: float,
    positioning_score: float,
    body_usage_score: float,
    position: str | None,
    height_cm: float | None,
    consistency: float | None,
) -> DeepAnalysis:
    """最新スコアから深掘り分析一式を導出する。"""
    scores = {
        _SPRINT: sprint_score,
        _BALL: ball_control_score,
        _POS: positioning_score,
        _BODY: body_usage_score,
    }
    return DeepAnalysis(
        abilities=compute_abilities(scores),
        duel=compute_duel(scores),
        footedness=compute_footedness(scores),
        situational=compute_situational(scores),
        heatmap=compute_heatmap(position, scores),
        decision=compute_decision(scores),
        set_piece=compute_set_piece(scores, height_cm),
        fatigue=compute_fatigue(scores, consistency),
    )
