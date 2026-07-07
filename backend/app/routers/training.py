"""練習メニューエンドポイント(#11)。

POST   /api/training/generate  — 弱点に基づくメニューを自動生成
GET    /api/training           — 自分のメニュー一覧
GET    /api/training/{id}      — メニュー詳細
DELETE /api/training/{id}      — メニュー削除

認証: 選手ロールのみ。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AthleteOnly
from app.schemas.training import GenerateMenuRequest, TrainingMenuResponse
from app.services import training_service

router = APIRouter()


@router.post(
    "/generate",
    response_model=TrainingMenuResponse,
    status_code=status.HTTP_201_CREATED,
    summary="練習メニューを自動生成する",
)
def generate_menu(
    req: GenerateMenuRequest,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> TrainingMenuResponse:
    """最新分析スコアの弱点を重点強化する練習メニューを生成する。"""
    menu = training_service.generate_menu(db, current_user, req.target_duration_min)
    return TrainingMenuResponse.model_validate(menu)


@router.get(
    "",
    response_model=list[TrainingMenuResponse],
    summary="自分の練習メニュー一覧を取得する",
)
def list_menus(
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[TrainingMenuResponse]:
    """練習メニューを新しい順に取得する。"""
    menus = training_service.list_menus(db, current_user, limit=limit, offset=offset)
    return [TrainingMenuResponse.model_validate(m) for m in menus]


@router.get(
    "/{menu_id}",
    response_model=TrainingMenuResponse,
    summary="練習メニュー詳細を取得する",
)
def get_menu(
    menu_id: uuid.UUID,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> TrainingMenuResponse:
    """練習メニューを 1 件取得する。本人のみ。"""
    menu = training_service.get_menu(db, current_user, menu_id)
    return TrainingMenuResponse.model_validate(menu)


@router.delete(
    "/{menu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="練習メニューを削除する",
)
def delete_menu(
    menu_id: uuid.UUID,
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """練習メニューを削除する。本人のみ。"""
    training_service.delete_menu(db, current_user, menu_id)
    return None
