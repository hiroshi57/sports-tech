"""スカウトCRM サービス(外販 C#25-27, C#30)。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.athlete import AthleteProfile
from app.models.crm import AthleteNote, ContactLog, ContactStage, ProfileViewLog, VideoClip
from app.models.user import User
from app.models.video import AnalysisResult, Video

# ── C#25: 接触ログ ────────────────────────────────────────────────


@dataclass(frozen=True)
class ContactWithAthlete:
    """接触ログ＋パイプライン表示用の選手情報。"""

    contact: ContactLog
    athlete_name: str | None
    athlete_position: str | None
    athlete_total_score: float | None


def _latest_total(db: Session, athlete_profile_id: uuid.UUID) -> float | None:
    """選手の最新分析の総合スコア（無ければ None）。"""
    return db.execute(
        select(AnalysisResult.total_score)
        .join(Video, Video.id == AnalysisResult.video_id)
        .where(Video.athlete_id == athlete_profile_id)
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def enrich_contact(db: Session, log: ContactLog) -> ContactWithAthlete:
    """接触ログに選手名・ポジション・最新スコアを付与する。"""
    profile = db.get(AthleteProfile, log.athlete_profile_id)
    return ContactWithAthlete(
        contact=log,
        athlete_name=profile.name if profile else None,
        athlete_position=profile.position if profile else None,
        athlete_total_score=_latest_total(db, log.athlete_profile_id) if profile else None,
    )


def _parse_stage(stage: str) -> ContactStage:
    try:
        return ContactStage(stage)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不正なステージ: {stage}",
        )


def _require_athlete(db: Session, athlete_profile_id: uuid.UUID) -> AthleteProfile:
    profile = db.get(AthleteProfile, athlete_profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="選手が見つかりません")
    return profile


def create_contact(
    db: Session,
    scout: User,
    athlete_profile_id: uuid.UUID,
    stage: str,
    note: str | None,
    contacted_at: datetime | None,
) -> ContactLog:
    _require_athlete(db, athlete_profile_id)
    log = ContactLog(
        id=uuid.uuid4(),
        scout_user_id=scout.id,
        athlete_profile_id=athlete_profile_id,
        stage=_parse_stage(stage),
        note=note,
        contacted_at=contacted_at,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_contacts(db: Session, scout: User, stage: str | None = None) -> list[ContactLog]:
    stmt = select(ContactLog).where(ContactLog.scout_user_id == scout.id)
    if stage:
        stmt = stmt.where(ContactLog.stage == _parse_stage(stage))
    stmt = stmt.order_by(ContactLog.updated_at.desc())
    return list(db.execute(stmt).scalars().all())


def _own_contact(db: Session, scout: User, contact_id: uuid.UUID) -> ContactLog:
    log = db.get(ContactLog, contact_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="接触ログが見つかりません"
        )
    if log.scout_user_id != scout.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="他人の接触ログです")
    return log


def update_contact(
    db: Session,
    scout: User,
    contact_id: uuid.UUID,
    *,
    stage: str | None,
    note: str | None,
    contacted_at: datetime | None,
) -> ContactLog:
    log = _own_contact(db, scout, contact_id)
    if stage is not None:
        log.stage = _parse_stage(stage)
    if note is not None:
        log.note = note
    if contacted_at is not None:
        log.contacted_at = contacted_at
    db.commit()
    db.refresh(log)
    return log


def delete_contact(db: Session, scout: User, contact_id: uuid.UUID) -> None:
    log = _own_contact(db, scout, contact_id)
    db.delete(log)
    db.commit()


def pipeline_summary(db: Session, scout: User) -> list[tuple[str, int]]:
    """ステージ別件数（商談パイプラインの俯瞰）。"""
    rows = db.execute(
        select(ContactLog.stage, func.count())
        .where(ContactLog.scout_user_id == scout.id)
        .group_by(ContactLog.stage)
    ).all()
    counts = {stage.value: count for stage, count in rows}
    return [(s.value, counts.get(s.value, 0)) for s in ContactStage]


# ── C#26: 共有ノート ──────────────────────────────────────────────


def create_note(db: Session, author: User, athlete_profile_id: uuid.UUID, body: str) -> AthleteNote:
    _require_athlete(db, athlete_profile_id)
    note = AthleteNote(
        id=uuid.uuid4(),
        author_user_id=author.id,
        athlete_profile_id=athlete_profile_id,
        body=body,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(db: Session, athlete_profile_id: uuid.UUID) -> list[AthleteNote]:
    stmt = (
        select(AthleteNote)
        .where(AthleteNote.athlete_profile_id == athlete_profile_id)
        .order_by(AthleteNote.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def delete_note(db: Session, author: User, note_id: uuid.UUID) -> None:
    note = db.get(AthleteNote, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ノートが見つかりません")
    if note.author_user_id != author.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="他人のノートです")
    db.delete(note)
    db.commit()


# ── C#27: 動画クリップ ────────────────────────────────────────────


def create_clip(
    db: Session,
    creator: User,
    video_id: uuid.UUID,
    *,
    title: str,
    start_sec: float,
    end_sec: float,
    comment: str | None,
) -> VideoClip:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="動画が見つかりません")
    if video.duration_sec is not None and end_sec > video.duration_sec:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"end_sec が動画の長さ({video.duration_sec}s)を超えています",
        )
    clip = VideoClip(
        id=uuid.uuid4(),
        video_id=video_id,
        creator_user_id=creator.id,
        title=title,
        start_sec=start_sec,
        end_sec=end_sec,
        comment=comment,
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)
    return clip


def list_clips(db: Session, video_id: uuid.UUID) -> list[VideoClip]:
    stmt = (
        select(VideoClip).where(VideoClip.video_id == video_id).order_by(VideoClip.start_sec.asc())
    )
    return list(db.execute(stmt).scalars().all())


def delete_clip(db: Session, creator: User, clip_id: uuid.UUID) -> None:
    clip = db.get(VideoClip, clip_id)
    if clip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="クリップが見つかりません"
        )
    if clip.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="他人のクリップです")
    db.delete(clip)
    db.commit()


# ── C#30: 閲覧ログ ────────────────────────────────────────────────


def record_view(db: Session, viewer: User, athlete_profile_id: uuid.UUID) -> None:
    """スカウトの選手カルテ閲覧を記録する（失敗しても本処理は妨げない）。"""
    db.add(
        ProfileViewLog(
            id=uuid.uuid4(),
            viewer_user_id=viewer.id,
            athlete_profile_id=athlete_profile_id,
        )
    )
    db.commit()


# ── 保護者同意・プライバシー（D#32/35） ──────────────────────────

VIDEO_RETENTION_DAYS = 90  # D#35 保存期間ポリシーと一致させる


def _is_minor(birth: date | None, today: date | None = None) -> bool:
    if birth is None:
        return False
    today = today or date.today()
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    return age < 18


def get_consent(user: User) -> dict:
    """選手本人の保護者同意・プライバシー状態を返す。"""
    return {
        "is_minor": _is_minor(user.birth_date),
        "consent_granted": bool(user.parental_consent),
        "guardian_name": None,
        "updated_at": user.updated_at,
        "video_retention_days": VIDEO_RETENTION_DAYS,
    }


def set_consent(db: Session, user: User, granted: bool) -> dict:
    """保護者同意を更新する（取消で公開停止に相当）。"""
    user.parental_consent = granted
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_consent(user)


def view_summary(db: Session, athlete_user: User, *, recent_limit: int = 20):
    """選手本人向け: 自分のカルテが誰(ロール)にいつ見られたか。"""
    profile = db.execute(
        select(AthleteProfile).where(AthleteProfile.user_id == athlete_user.id)
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="選手プロフィールがありません"
        )
    rows = db.execute(
        select(ProfileViewLog, User.role)
        .join(User, User.id == ProfileViewLog.viewer_user_id)
        .where(ProfileViewLog.athlete_profile_id == profile.id)
        .order_by(ProfileViewLog.created_at.desc())
    ).all()
    total = len(rows)
    cutoff = datetime.now(UTC) - timedelta(days=30)
    last30 = 0
    for log, _role in rows:
        created = log.created_at
        if created is not None and created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if created is not None and created >= cutoff:
            last30 += 1
    recent = [(role.value, log.created_at) for log, role in rows[:recent_limit]]
    return total, last30, recent
