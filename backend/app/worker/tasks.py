"""動画分析 Celery タスク。

フロー:
1. complete_upload が analyze_video.delay(video_id) を呼ぶ
2. ワーカーが動画を PROCESSING に更新
3. 分析エンジン（現在はスタブ）でスコア算出
4. AnalysisResult を保存し COMPLETED に更新
5. 失敗時は最大 3 回リトライし、それでも失敗なら FAILED に更新
"""

from __future__ import annotations

import logging
import uuid

from app.core.database import SessionLocal
from app.models.athlete import AthleteProfile
from app.models.video import AnalysisResult, Video, VideoStatus
from app.services import analysis_engine, notification_service
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _resolve_user_id(db, athlete_id: uuid.UUID) -> uuid.UUID | None:
    """athlete_id から通知先の user_id を解決する。"""
    profile = db.get(AthleteProfile, athlete_id)
    return profile.user_id if profile is not None else None


MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 30


@celery_app.task(
    bind=True,
    name="app.worker.tasks.analyze_video",
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF_SEC,
)
def analyze_video(self, video_id: str) -> dict:
    """
    動画を AI 分析してスコアを保存する。

    Args:
        video_id: 対象動画の UUID（文字列）

    Returns:
        {"video_id": ..., "status": ..., "total_score": ...}
    """
    vid = uuid.UUID(video_id)
    db = SessionLocal()
    try:
        video = db.get(Video, vid)
        if video is None:
            logger.warning("analyze_video: video %s not found — skip", video_id)
            return {"video_id": video_id, "status": "not_found"}

        if video.status == VideoStatus.COMPLETED:
            logger.info("analyze_video: video %s already completed — skip", video_id)
            return {"video_id": video_id, "status": VideoStatus.COMPLETED.value}

        # ── PROCESSING に遷移 ───────────────────────────────────────
        video.status = VideoStatus.PROCESSING
        db.commit()

        try:
            # ── 分析実行（現在はスタブエンジン）─────────────────────
            scores = analysis_engine.analyze(video.id, video.s3_key)

            # ── 結果保存（再実行時は既存結果を置き換え）─────────────
            existing = (
                db.query(AnalysisResult).filter(AnalysisResult.video_id == video.id).one_or_none()
            )
            if existing is not None:
                db.delete(existing)
                db.flush()

            result = AnalysisResult(
                id=uuid.uuid4(),
                video_id=video.id,
                sprint_score=scores.sprint_score,
                ball_control_score=scores.ball_control_score,
                positioning_score=scores.positioning_score,
                body_usage_score=scores.body_usage_score,
                total_score=scores.total_score,
                confidence=scores.confidence,
                feedback=scores.feedback,
            )
            db.add(result)
            video.status = VideoStatus.COMPLETED
            athlete_id = video.athlete_id
            db.commit()

            # ── 分析完了通知（失敗しても本処理は止めない）─────────────
            user_id = _resolve_user_id(db, athlete_id)
            if user_id is not None:
                notification_service.notify_analysis_completed(db, user_id, vid)

            logger.info(
                "analyze_video: video %s completed (total=%s)", video_id, scores.total_score
            )
            return {
                "video_id": video_id,
                "status": VideoStatus.COMPLETED.value,
                "total_score": scores.total_score,
            }

        except Exception as exc:
            db.rollback()
            if self.request.retries < MAX_RETRIES:
                logger.warning(
                    "analyze_video: video %s failed (attempt %d/%d): %s — retrying",
                    video_id,
                    self.request.retries + 1,
                    MAX_RETRIES,
                    exc,
                )
                raise self.retry(exc=exc) from exc

            # リトライ上限到達 → FAILED に更新
            video = db.get(Video, vid)
            if video is not None:
                video.status = VideoStatus.FAILED
                athlete_id = video.athlete_id
                db.commit()
                user_id = _resolve_user_id(db, athlete_id)
                if user_id is not None:
                    notification_service.notify_analysis_failed(db, user_id, vid)
            logger.error("analyze_video: video %s permanently failed: %s", video_id, exc)
            return {"video_id": video_id, "status": VideoStatus.FAILED.value, "error": str(exc)}
    finally:
        db.close()


def dispatch_analysis(video_id: uuid.UUID) -> str | None:
    """
    分析タスクをキューに投入する。

    broker 到達不能でも API リクエストは失敗させない（動画は PENDING のまま残り、
    後述の再投入バッチ or 手動リトライで回収する想定）。

    Returns:
        Celery タスク ID（投入失敗時は None）
    """
    try:
        async_result = analyze_video.delay(str(video_id))
        return async_result.id
    except Exception as exc:  # broker 接続エラー等
        logger.error("dispatch_analysis: failed to enqueue video %s: %s", video_id, exc)
        return None
