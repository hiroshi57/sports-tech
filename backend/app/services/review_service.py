"""練習振り返りサービス(#12)。

動画（＋AI分析スコア）に紐づけて振り返りを記録する。
video_id を指定する場合、その動画が本人のものであることを検証する。
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.athlete import AthleteProfile
from app.models.review import PracticeReview
from app.models.user import User
from app.models.video import Video
from app.schemas.review import ReviewCreate, ReviewUpdate


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


def _validate_video_ownership(db: Session, video_id: uuid.UUID, athlete_id: uuid.UUID) -> None:
    """振り返り対象の動画が本人のものか検証する。"""
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="対象の動画が見つかりません",
        )
    if video.athlete_id != athlete_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この動画に振り返りを作成する権限がありません",
        )


def create_review(db: Session, user: User, req: ReviewCreate) -> PracticeReview:
    """振り返りを作成する。"""
    profile = _get_profile(db, user)
    if req.video_id is not None:
        _validate_video_ownership(db, req.video_id, profile.id)

    review = PracticeReview(
        id=uuid.uuid4(),
        athlete_id=profile.id,
        video_id=req.video_id,
        self_rating=req.self_rating,
        went_well=req.went_well,
        to_improve=req.to_improve,
        notes=req.notes,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_reviews(
    db: Session,
    user: User,
    *,
    video_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[PracticeReview]:
    """自分の振り返り一覧を取得する（新しい順）。video_id で絞り込み可能。"""
    profile = _get_profile(db, user)
    stmt = select(PracticeReview).where(PracticeReview.athlete_id == profile.id)
    if video_id is not None:
        stmt = stmt.where(PracticeReview.video_id == video_id)
    stmt = stmt.order_by(PracticeReview.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


def get_review(db: Session, user: User, review_id: uuid.UUID) -> PracticeReview:
    """振り返りを 1 件取得する（本人のみ）。"""
    return _get_owned_review(db, user, review_id)


def update_review(
    db: Session, user: User, review_id: uuid.UUID, req: ReviewUpdate
) -> PracticeReview:
    """振り返りを更新する（指定フィールドのみ）。"""
    review = _get_owned_review(db, user, review_id)
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, user: User, review_id: uuid.UUID) -> None:
    """振り返りを削除する（本人のみ）。"""
    review = _get_owned_review(db, user, review_id)
    db.delete(review)
    db.commit()


def _get_owned_review(db: Session, user: User, review_id: uuid.UUID) -> PracticeReview:
    profile = _get_profile(db, user)
    review = db.get(PracticeReview, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="振り返りが見つかりません",
        )
    if review.athlete_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この振り返りへのアクセス権限がありません",
        )
    return review
