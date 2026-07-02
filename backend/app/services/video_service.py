"""動画アップロード・管理サービス。

フロー:
1. クライアントが POST /videos/upload-url を呼ぶ
2. サーバーが S3 Presigned URL と video_id を返す（DB にレコード作成）
3. クライアントが Presigned URL に直接 PUT で動画をアップロード
4. クライアントが POST /videos/{id}/complete を呼ぶ（ステータスを PENDING に）
5. バックエンドが Celery タスクをキューに投入して分析を開始する
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import s3 as s3_client
from app.models.athlete import AthleteProfile
from app.models.user import User, UserRole
from app.models.video import Video, VideoStatus
from app.schemas.video import VideoUploadInitRequest


def _get_athlete_profile(db: Session, user: User) -> AthleteProfile:
    """ユーザーに紐づく選手プロフィールを取得する。"""
    profile = db.execute(
        select(AthleteProfile).where(AthleteProfile.user_id == user.id)
    ).scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="選手プロフィールが未登録です。先にプロフィールを作成してください。",
        )
    return profile


def initiate_upload(
    db: Session,
    user: User,
    req: VideoUploadInitRequest,
) -> tuple[Video, str]:
    """
    動画アップロードを開始する。

    1. MIME タイプ・ファイルサイズを検証
    2. S3 キーを生成
    3. DB に Video レコードを作成（status=PENDING）
    4. Presigned PUT URL を生成して返す

    Args:
        db: DB セッション
        user: 認証済みユーザー（athlete ロール必須）
        req: アップロード開始リクエスト

    Returns:
        (Video オブジェクト, Presigned PUT URL)
    """
    # ── ロール検証: 選手のみアップロード可 ──────────────────────────
    if user.role != UserRole.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="動画アップロードは選手ロールのみ可能です",
        )

    # ── MIME タイプ検証 ─────────────────────────────────────────────
    if not s3_client.validate_mime_type(req.content_type):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"未対応のファイル形式です。対応形式: {sorted(s3_client.ALLOWED_MIME_TYPES)}",
        )

    # ── ファイルサイズ検証 ──────────────────────────────────────────
    if req.file_size_bytes is not None and not s3_client.validate_file_size(req.file_size_bytes):
        max_mb = s3_client.MAX_FILE_SIZE_BYTES // 1024 // 1024
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ファイルサイズが上限（{max_mb} MB）を超えています",
        )

    # ── 選手プロフィール取得 ────────────────────────────────────────
    profile = _get_athlete_profile(db, user)

    # ── S3 キー生成 ─────────────────────────────────────────────────
    s3_key = s3_client.build_s3_key(profile.id, req.filename)

    # ── DB に Video レコード作成 ────────────────────────────────────
    video = Video(
        id=uuid.uuid4(),
        athlete_id=profile.id,
        s3_key=s3_key,
        original_filename=req.filename,
        file_size_bytes=req.file_size_bytes,
        mime_type=req.content_type,
        status=VideoStatus.PENDING,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    # ── Presigned URL 生成 ──────────────────────────────────────────
    presigned_url = s3_client.generate_presigned_upload_url(
        s3_key=s3_key,
        content_type=req.content_type,
    )

    return video, presigned_url


def complete_upload(db: Session, video_id: uuid.UUID, user: User) -> Video:
    """
    動画アップロード完了を通知する。

    クライアントが S3 への PUT を終えた後に呼ぶ。
    ステータスを PENDING のまま維持し、Celery タスク投入の準備をする。

    NOTE:
        実際の Celery タスク投入は Phase 2（AI分析エンジン）で実装する。
        現段階では status を PENDING に保つだけ。

    Returns:
        更新された Video オブジェクト
    """
    video = _get_video_owned_by_user(db, video_id, user)

    if video.status != VideoStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"この動画は既に処理中です (status={video.status.value})",
        )

    # TODO (Phase 2): Celery タスクをキューに投入
    # task = analyze_video.delay(str(video.id))
    # video.celery_task_id = task.id

    db.commit()
    db.refresh(video)
    return video


def get_video(db: Session, video_id: uuid.UUID, user: User) -> Video:
    """動画情報を取得する（所有者のみ）。"""
    return _get_video_owned_by_user(db, video_id, user)


def list_videos(
    db: Session,
    user: User,
    limit: int = 20,
    offset: int = 0,
) -> list[Video]:
    """自分の動画一覧を取得する。"""
    profile = _get_athlete_profile(db, user)
    stmt = (
        select(Video)
        .where(Video.athlete_id == profile.id)
        .order_by(Video.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all())


def delete_video(db: Session, video_id: uuid.UUID, user: User) -> None:
    """
    動画を削除する（S3 オブジェクトも削除）。

    分析処理中（PROCESSING）の動画は削除できない。
    """
    video = _get_video_owned_by_user(db, video_id, user)

    if video.status == VideoStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="分析処理中の動画は削除できません",
        )

    # S3 から削除（冪等なので存在しなくてもエラーにならない）
    s3_client.delete_s3_object(video.s3_key)

    db.delete(video)
    db.commit()


def get_video_download_url(db: Session, video_id: uuid.UUID, user: User) -> str:
    """動画の再生用 Presigned GET URL を生成する。"""
    video = _get_video_owned_by_user(db, video_id, user)

    if video.status == VideoStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="アップロードが完了していない動画は再生できません",
        )

    return s3_client.generate_presigned_download_url(video.s3_key)


# ── プライベートヘルパー ───────────────────────────────────────────


def _get_video_owned_by_user(db: Session, video_id: uuid.UUID, user: User) -> Video:
    """
    指定 ID の動画を取得し、所有者チェックを行う。

    Raises:
        404: 動画が存在しない
        403: 動画の所有者でない
    """
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="動画が見つかりません",
        )

    # 所有者チェック: video.athlete_id → athlete_profile.user_id == user.id
    profile = db.get(AthleteProfile, video.athlete_id)
    if profile is None or profile.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この動画へのアクセス権限がありません",
        )

    return video
