"""動画管理エンドポイント。

POST   /api/videos/upload-url      — アップロード開始（Presigned URL 発行）
POST   /api/videos/{id}/complete   — アップロード完了通知
GET    /api/videos                 — 自分の動画一覧
GET    /api/videos/{id}            — 動画詳細
GET    /api/videos/{id}/download   — 再生用 Presigned URL 取得
DELETE /api/videos/{id}            — 動画削除

認証: 全エンドポイントで Bearer JWT 必須。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AthleteOnly, CurrentUser
from app.schemas.video import (
    AnalysisResultResponse,
    VideoCompleteRequest,
    VideoDownloadUrlResponse,
    VideoResponse,
    VideoUploadInitRequest,
    VideoUploadResponse,
)
from app.services import billing_service, video_service
from app.services.billing_service import QuotaExceededError

router = APIRouter()


@router.post(
    "/upload-url",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="動画アップロード URL を発行する",
)
def initiate_upload(
    req: VideoUploadInitRequest,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> VideoUploadResponse:
    """
    S3 Presigned PUT URL を発行する。

    1. このエンドポイントを呼ぶ → `presigned_url` と `video_id` を取得
    2. `presigned_url` に `Content-Type` ヘッダー付きで PUT リクエストを送信
    3. PUT が成功したら `POST /videos/{video_id}/complete` を呼ぶ

    選手ロールのみ利用可能。
    """
    video, presigned_url = video_service.initiate_upload(db, current_user, req)
    return VideoUploadResponse(
        video_id=video.id,
        presigned_url=presigned_url,
        s3_key=video.s3_key,
    )


@router.post(
    "/{video_id}/complete",
    response_model=VideoResponse,
    summary="動画アップロード完了を通知する",
)
def complete_upload(
    video_id: uuid.UUID,
    req: VideoCompleteRequest,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> VideoResponse:
    """
    S3 への PUT アップロードが完了した後に呼ぶ。

    - 動画の長さ（秒）を記録する
    - AI 分析キューへの投入準備をする（Phase 2 で実装）

    フリーミアムのクォータ(E#38): 当月の分析枠を超過している場合は 402 を返す。
    完了＝分析1本の消費として当期利用量をカウントする。
    """
    # クォータ判定（無料枠超過は 402 Payment Required でアップグレードへ誘導）
    try:
        billing_service.check_can_analyze(db, current_user)
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=e.message,
        )

    video = video_service.complete_upload(db, video_id, current_user)
    # duration_sec を更新
    if req.duration_sec is not None:
        video.duration_sec = req.duration_sec
        db.commit()
        db.refresh(video)

    # 分析1本を消費として記録
    billing_service.record_analysis(db, current_user)
    return VideoResponse.model_validate(video)


@router.get(
    "",
    response_model=list[VideoResponse],
    summary="自分の動画一覧を取得する",
)
def list_videos(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[VideoResponse]:
    """
    ログイン中の選手が所有する動画一覧を返す。

    `limit` / `offset` でページネーション可能。
    """
    videos = video_service.list_videos(db, current_user, limit=limit, offset=offset)
    return [VideoResponse.model_validate(v) for v in videos]


@router.get(
    "/{video_id}",
    response_model=VideoResponse,
    summary="動画詳細を取得する",
)
def get_video(
    video_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> VideoResponse:
    """動画のメタデータと処理ステータスを返す。所有者のみアクセス可能。"""
    video = video_service.get_video(db, video_id, current_user)
    return VideoResponse.model_validate(video)


@router.get(
    "/{video_id}/analysis",
    response_model=AnalysisResultResponse,
    summary="動画の AI 分析結果を取得する",
)
def get_video_analysis(
    video_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> AnalysisResultResponse:
    """
    AI 分析結果（5 スコア + フィードバック）を返す。所有者のみアクセス可能。

    スコアは参考値（`is_reference_score: true`）であり、
    選手評価の唯一の根拠として使用しないこと。
    """
    result = video_service.get_video_analysis(db, video_id, current_user)
    # ポジション別重み(B#18)で内訳を算出するため所有者のポジションを解決
    from sqlalchemy import select

    from app.models.athlete import AthleteProfile

    position = db.execute(
        select(AthleteProfile.position).where(AthleteProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    return AnalysisResultResponse.from_orm_with_alias(result, position=position)


@router.get(
    "/{video_id}/download",
    response_model=VideoDownloadUrlResponse,
    summary="動画再生用 URL を取得する",
)
def get_download_url(
    video_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> VideoDownloadUrlResponse:
    """
    動画再生用の Presigned GET URL を発行する（有効期限 1 時間）。

    PENDING 状態（S3 未到達）の動画はエラーになる。
    """
    url = video_service.get_video_download_url(db, video_id, current_user)
    return VideoDownloadUrlResponse(video_id=video_id, download_url=url)


@router.delete(
    "/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="動画を削除する",
)
def delete_video(
    video_id: uuid.UUID,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """
    動画と S3 オブジェクトを削除する。

    分析処理中（PROCESSING）の動画は削除できない。
    """
    video_service.delete_video(db, video_id, current_user)
    return None
