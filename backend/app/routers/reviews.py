"""練習振り返りエンドポイント(#12)。

POST   /api/reviews          — 振り返りを作成
GET    /api/reviews          — 自分の振り返り一覧（video_id で絞込可）
GET    /api/reviews/{id}     — 振り返り詳細
PATCH  /api/reviews/{id}     — 振り返り更新
DELETE /api/reviews/{id}     — 振り返り削除

認証: 選手ロールのみ。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AthleteOnly
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.services import review_service

router = APIRouter()


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="練習振り返りを作成する",
)
def create_review(
    req: ReviewCreate,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> ReviewResponse:
    """動画（任意）に紐づけて振り返りを記録する。選手ロールのみ。"""
    review = review_service.create_review(db, current_user, req)
    return ReviewResponse.model_validate(review)


@router.get(
    "",
    response_model=list[ReviewResponse],
    summary="自分の振り返り一覧を取得する",
)
def list_reviews(
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
    video_id: uuid.UUID | None = Query(None, description="特定動画の振り返りに絞り込む"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ReviewResponse]:
    """振り返りを新しい順に取得する。"""
    reviews = review_service.list_reviews(
        db, current_user, video_id=video_id, limit=limit, offset=offset
    )
    return [ReviewResponse.model_validate(r) for r in reviews]


@router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="振り返り詳細を取得する",
)
def get_review(
    review_id: uuid.UUID,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> ReviewResponse:
    """振り返りを 1 件取得する。本人のみ。"""
    review = review_service.get_review(db, current_user, review_id)
    return ReviewResponse.model_validate(review)


@router.patch(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="振り返りを更新する",
)
def update_review(
    review_id: uuid.UUID,
    req: ReviewUpdate,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> ReviewResponse:
    """振り返りを更新する（指定フィールドのみ）。本人のみ。"""
    review = review_service.update_review(db, current_user, review_id, req)
    return ReviewResponse.model_validate(review)


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="振り返りを削除する",
)
def delete_review(
    review_id: uuid.UUID,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """振り返りを削除する。本人のみ。"""
    review_service.delete_review(db, current_user, review_id)
    return None
