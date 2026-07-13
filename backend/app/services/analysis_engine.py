"""AI 分析エンジン。

MediaPipe による姿勢推定 → 運動学的スコアリングを実行する。
mediapipe / opencv が利用できない環境（テスト・未構築環境）や、
動画が短すぎてポーズを抽出できない場合は決定論的スタブにフォールバックする。

パイプライン:
1. S3 から動画ダウンロード（pose_estimation.extract_pose_from_s3）
2. MediaPipe で 33 ランドマーク時系列を抽出
3. scoring モジュールで 4 スコアを算出
4. 総合スコアを加重平均で算出

スコア算出ロジックの本格モデルへの差し替えは外販ロードマップ #4〜#7、
精度検証は #21 で行う。
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass

from app.services import position_weights, scoring
from app.services.pose_estimation import (
    PoseEstimationError,
    PoseSequence,
    extract_pose_from_s3,
)
from app.services.scoring import MIN_FRAMES_FOR_SCORING

logger = logging.getLogger(__name__)

# スタブ実装の信頼度（本実装で動画品質から算出する）
STUB_CONFIDENCE = 0.1

STUB_FEEDBACK = (
    "【開発中】このスコアはプレースホルダーです。"
    "AI 分析エンジン（姿勢推定）は現在開発中のため、正式なスコアではありません。"
    "スコアはあくまで参考値であり、選手評価の唯一の根拠として使用しないでください。"
)

# 姿勢推定成功時の基準信頼度（Phase 1 ヒューリスティックのため控えめ）
POSE_BASE_CONFIDENCE = 0.5

POSE_FEEDBACK = (
    "姿勢推定に基づく分析結果です（Phase 1 ヒューリスティック）。"
    "ボールコントロールは下肢の動作から近似しており、精度は限定的です。"
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


def analyze(video_id: uuid.UUID, s3_key: str, position: str | None = None) -> AnalysisScores:
    """
    動画を分析してスコアを返す。

    姿勢推定パイプラインを試み、利用不可 or 失敗時はスタブにフォールバックする。
    総合スコアはポジション別の重み(B#18)で算出する。

    Args:
        video_id: 対象動画の ID
        s3_key: S3 オブジェクトキー
        position: 選手ポジション（FW/MF/DF/GK）。None は balanced 重み。

    Returns:
        AnalysisScores
    """
    try:
        seq = extract_pose_from_s3(s3_key)
    except PoseEstimationError as exc:
        logger.info("姿勢推定を利用できません（%s）— スタブにフォールバック", exc)
        return _stub_scores(video_id, position)
    except Exception as exc:  # 動画破損・DL 失敗など
        logger.warning("姿勢推定に失敗（video=%s）: %s — スタブにフォールバック", video_id, exc)
        return _stub_scores(video_id, position)

    if len(seq.frames) < MIN_FRAMES_FOR_SCORING:
        logger.info(
            "ポーズ検出フレームが不足（%d < %d）— スタブにフォールバック",
            len(seq.frames),
            MIN_FRAMES_FOR_SCORING,
        )
        return _stub_scores(video_id, position)

    return _score_from_pose(seq, position)


def _score_from_pose(seq: PoseSequence, position: str | None = None) -> AnalysisScores:
    """ポーズ時系列からスコアを算出する。"""
    sprint = scoring.compute_sprint_score(seq)
    ball = scoring.compute_ball_control_score(seq)
    positioning = scoring.compute_positioning_score(seq)
    body = scoring.compute_body_usage_score(seq)

    total = position_weights.weighted_total(sprint, ball, positioning, body, position)

    return AnalysisScores(
        sprint_score=sprint,
        ball_control_score=ball,
        positioning_score=positioning,
        body_usage_score=body,
        total_score=total,
        confidence=POSE_BASE_CONFIDENCE,
        feedback=POSE_FEEDBACK,
    )


def _stub_scores(video_id: uuid.UUID, position: str | None = None) -> AnalysisScores:
    """決定論的スタブスコア（姿勢推定が使えない場合のフォールバック）。"""
    sprint = _deterministic_score(video_id, "sprint")
    ball = _deterministic_score(video_id, "ball_control")
    positioning = _deterministic_score(video_id, "positioning")
    body = _deterministic_score(video_id, "body_usage")

    total = position_weights.weighted_total(sprint, ball, positioning, body, position)

    return AnalysisScores(
        sprint_score=sprint,
        ball_control_score=ball,
        positioning_score=positioning,
        body_usage_score=body,
        total_score=total,
        confidence=STUB_CONFIDENCE,
        feedback=STUB_FEEDBACK,
    )
