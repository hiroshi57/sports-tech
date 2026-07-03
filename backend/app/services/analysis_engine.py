"""AI 分析エンジン（Phase 2 スタブ実装）。

現段階では MediaPipe / 姿勢推定は未接続のため、動画 ID から決定論的に
プレースホルダースコアを生成する。confidence を低く設定し、
フィードバックにスタブであることを明記する。

Phase 2 で以下に置き換える:
- S3 から動画ダウンロード
- MediaPipe による骨格抽出
- スプリント / ボールコントロール / ポジショニング / 身体の使い方の各スコア算出
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

# スタブ実装の信頼度（本実装で動画品質から算出する）
STUB_CONFIDENCE = 0.1

STUB_FEEDBACK = (
    "【開発中】このスコアはプレースホルダーです。"
    "AI 分析エンジン（姿勢推定）は現在開発中のため、正式なスコアではありません。"
    "スコアはあくまで参考値であり、選手評価の唯一の根拠として使用しないでください。"
)


@dataclass(frozen=True)
class AnalysisScores:
    """分析スコア一式（各 0〜100）。"""

    sprint_score: float
    ball_control_score: float
    positioning_score: float
    body_usage_score: float
    total_score: float
    confidence: float
    feedback: str


def _deterministic_score(video_id: uuid.UUID, salt: str) -> float:
    """動画 ID + salt から 40〜85 の決定論的スコアを生成する（スタブ）。"""
    digest = hashlib.sha256(f"{video_id}:{salt}".encode()).digest()
    value = int.from_bytes(digest[:4], "big") % 4600  # 0〜4599
    return round(40.0 + value / 100.0, 1)  # 40.0〜85.9


def analyze(video_id: uuid.UUID, s3_key: str) -> AnalysisScores:
    """
    動画を分析してスコアを返す。

    Args:
        video_id: 対象動画の ID
        s3_key: S3 オブジェクトキー（Phase 2 でダウンロードに使用）

    Returns:
        AnalysisScores（現段階では決定論的スタブ値）
    """
    del s3_key  # Phase 2 で使用

    sprint = _deterministic_score(video_id, "sprint")
    ball = _deterministic_score(video_id, "ball_control")
    positioning = _deterministic_score(video_id, "positioning")
    body = _deterministic_score(video_id, "body_usage")

    # 総合スコア: 単純加重平均（重みは Phase 2 で調整）
    total = round(sprint * 0.3 + ball * 0.3 + positioning * 0.2 + body * 0.2, 1)

    return AnalysisScores(
        sprint_score=sprint,
        ball_control_score=ball,
        positioning_score=positioning,
        body_usage_score=body,
        total_score=total,
        confidence=STUB_CONFIDENCE,
        feedback=STUB_FEEDBACK,
    )
