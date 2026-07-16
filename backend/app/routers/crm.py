"""スカウトCRM エンドポイント(外販 C#25-27, C#30)。

C#25 接触ログ・パイプライン:
  POST/GET/PATCH/DELETE /api/scouts/contacts
  GET /api/scouts/contacts/pipeline

C#26 チーム内共有ノート:
  POST/GET/DELETE /api/scouts/notes

C#27 動画クリップ:
  POST/GET /api/scouts/videos/{video_id}/clips
  DELETE /api/scouts/clips/{clip_id}

C#30 閲覧履歴の選手側開示:
  GET /api/athletes/me/profile-views（選手本人）
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AthleteOnly, ScoutOrCoach
from app.schemas.crm import (
    AthleteNoteCreate,
    AthleteNoteResponse,
    ContactLogCreate,
    ContactLogResponse,
    ContactLogUpdate,
    PipelineSummary,
    ProfileViewResponse,
    ProfileViewSummary,
    VideoClipCreate,
    VideoClipResponse,
)
from app.services import crm_service

router = APIRouter()
athlete_router = APIRouter()


def _contact_to_response(log) -> ContactLogResponse:
    return ContactLogResponse(
        id=log.id,
        athlete_profile_id=log.athlete_profile_id,
        stage=log.stage.value,
        note=log.note,
        contacted_at=log.contacted_at,
        created_at=log.created_at,
        updated_at=log.updated_at,
    )


# ── C#25: 接触ログ ────────────────────────────────────────────────


@router.post(
    "/contacts",
    response_model=ContactLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="接触ログを記録する",
)
def create_contact(
    req: ContactLogCreate,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> ContactLogResponse:
    log = crm_service.create_contact(
        db, current_user, req.athlete_profile_id, req.stage, req.note, req.contacted_at
    )
    return _contact_to_response(log)


@router.get("/contacts", response_model=list[ContactLogResponse], summary="接触ログ一覧")
def list_contacts(
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
    stage: str | None = Query(None),
) -> list[ContactLogResponse]:
    return [_contact_to_response(c) for c in crm_service.list_contacts(db, current_user, stage)]


@router.get(
    "/contacts/pipeline",
    response_model=list[PipelineSummary],
    summary="商談パイプラインのステージ別件数",
)
def get_pipeline(
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> list[PipelineSummary]:
    return [
        PipelineSummary(stage=s, count=c) for s, c in crm_service.pipeline_summary(db, current_user)
    ]


@router.patch(
    "/contacts/{contact_id}", response_model=ContactLogResponse, summary="接触ログを更新する"
)
def update_contact(
    contact_id: uuid.UUID,
    req: ContactLogUpdate,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> ContactLogResponse:
    log = crm_service.update_contact(
        db,
        current_user,
        contact_id,
        stage=req.stage,
        note=req.note,
        contacted_at=req.contacted_at,
    )
    return _contact_to_response(log)


@router.delete(
    "/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="接触ログを削除する",
)
def delete_contact(
    contact_id: uuid.UUID,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    crm_service.delete_contact(db, current_user, contact_id)


# ── C#26: 共有ノート ──────────────────────────────────────────────


@router.post(
    "/notes",
    response_model=AthleteNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="選手への共有ノートを投稿する",
)
def create_note(
    req: AthleteNoteCreate,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> AthleteNoteResponse:
    note = crm_service.create_note(db, current_user, req.athlete_profile_id, req.body)
    return AthleteNoteResponse.model_validate(note)


@router.get(
    "/notes",
    response_model=list[AthleteNoteResponse],
    summary="選手の共有ノート一覧（チーム内）",
)
def list_notes(
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
    athlete_profile_id: uuid.UUID = Query(...),
) -> list[AthleteNoteResponse]:
    notes = crm_service.list_notes(db, athlete_profile_id)
    return [AthleteNoteResponse.model_validate(n) for n in notes]


@router.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="自分の共有ノートを削除する",
)
def delete_note(
    note_id: uuid.UUID,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    crm_service.delete_note(db, current_user, note_id)


# ── C#27: 動画クリップ ────────────────────────────────────────────


@router.post(
    "/videos/{video_id}/clips",
    response_model=VideoClipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="動画クリップを切り出す（区間メタデータ）",
)
def create_clip(
    video_id: uuid.UUID,
    req: VideoClipCreate,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> VideoClipResponse:
    clip = crm_service.create_clip(
        db,
        current_user,
        video_id,
        title=req.title,
        start_sec=req.start_sec,
        end_sec=req.end_sec,
        comment=req.comment,
    )
    return VideoClipResponse.model_validate(clip)


@router.get(
    "/videos/{video_id}/clips",
    response_model=list[VideoClipResponse],
    summary="動画のクリップ一覧",
)
def list_clips(
    video_id: uuid.UUID,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> list[VideoClipResponse]:
    return [VideoClipResponse.model_validate(c) for c in crm_service.list_clips(db, video_id)]


@router.delete(
    "/clips/{clip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="自分のクリップを削除する",
)
def delete_clip(
    clip_id: uuid.UUID,
    current_user: ScoutOrCoach,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    crm_service.delete_clip(db, current_user, clip_id)


# ── C#30: 閲覧履歴（選手本人向け） ────────────────────────────────


@athlete_router.get(
    "/me/profile-views",
    response_model=ProfileViewSummary,
    summary="自分のカルテ閲覧履歴（誰に見られたか）",
)
def get_my_profile_views(
    current_user: AthleteOnly,
    db: Annotated[Session, Depends(get_db)],
) -> ProfileViewSummary:
    total, last30, recent = crm_service.view_summary(db, current_user)
    return ProfileViewSummary(
        total_views=total,
        views_last_30d=last30,
        recent=[ProfileViewResponse(viewer_role=r, viewed_at=t) for r, t in recent],
    )
