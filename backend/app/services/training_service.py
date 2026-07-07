"""練習メニュー自動生成サービス(#11)。

選手の最新分析スコアから弱点スキルを特定し、それを重点的に鍛える
ドリルで練習メニューを構成する。分析がない場合は基礎メニューを返す。

ドリルライブラリは Phase 1 の固定テンプレート。将来は LLM 生成や
コーチ監修ライブラリに差し替える（外販ロードマップ #11 の発展）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.athlete import AthleteProfile
from app.models.training import TrainingMenu
from app.models.user import User
from app.models.video import AnalysisResult, Video, VideoStatus

# スキルごとのドリルライブラリ（target_skill, name, description, 標準時間）
_DRILL_LIBRARY: dict[str, list[dict]] = {
    "sprint": [
        {
            "name": "スプリントインターバル",
            "duration_min": 15,
            "description": "30m 全力ダッシュ×10本。加速局面を意識する。",
        },
        {
            "name": "ラダーステップ",
            "duration_min": 10,
            "description": "接地時間を短く、脚の回転を速くする。",
        },
    ],
    "ball_control": [
        {
            "name": "コーンドリブル",
            "duration_min": 15,
            "description": "細かいタッチでコーン間をジグザグ通過する。",
        },
        {
            "name": "壁当てトラップ",
            "duration_min": 10,
            "description": "壁パスを様々な部位でトラップし即コントロール。",
        },
    ],
    "positioning": [
        {
            "name": "3対1 ロンド",
            "duration_min": 15,
            "description": "パスコースを作る動き直しを繰り返す。",
        },
        {
            "name": "スモールサイドゲーム",
            "duration_min": 20,
            "description": "オフザボールの位置取りを意識した少人数ゲーム。",
        },
    ],
    "body_usage": [
        {
            "name": "体幹スタビリティ",
            "duration_min": 10,
            "description": "プランク系で体幹の安定性を高める。",
        },
        {
            "name": "片脚バランスドリル",
            "duration_min": 10,
            "description": "片脚立位でのボールタッチで軸の安定を養う。",
        },
    ],
}

_SKILL_LABELS = {
    "sprint": "スプリント",
    "ball_control": "ボールコントロール",
    "positioning": "ポジショニング",
    "body_usage": "身体の使い方",
}


@dataclass(frozen=True)
class _ScoreSet:
    sprint: float
    ball_control: float
    positioning: float
    body_usage: float


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


def _latest_scores(db: Session, athlete_id: uuid.UUID) -> _ScoreSet | None:
    row = db.execute(
        select(AnalysisResult)
        .join(Video, AnalysisResult.video_id == Video.id)
        .where(Video.athlete_id == athlete_id)
        .where(Video.status == VideoStatus.COMPLETED)
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    return _ScoreSet(
        sprint=row.sprint_score,
        ball_control=row.ball_control_score,
        positioning=row.positioning_score,
        body_usage=row.body_usage_score,
    )


def _difficulty_for(avg: float) -> str:
    if avg >= 90:
        return "elite"
    if avg >= 75:
        return "advanced"
    if avg >= 55:
        return "intermediate"
    return "beginner"


def generate_menu(db: Session, user: User, target_duration_min: int = 60) -> TrainingMenu:
    """最新スコアの弱点に基づく練習メニューを生成・保存する。"""
    profile = _get_profile(db, user)
    scores = _latest_scores(db, profile.id)

    if scores is None:
        # 分析データがない → バランス型の基礎メニュー
        skills_ordered = ["ball_control", "sprint", "positioning", "body_usage"]
        difficulty = "beginner"
        weak_desc = "分析データがまだないため、基礎バランスメニューを提案します。"
    else:
        skill_scores = {
            "sprint": scores.sprint,
            "ball_control": scores.ball_control,
            "positioning": scores.positioning,
            "body_usage": scores.body_usage,
        }
        # スコアが低い順（弱点優先）
        skills_ordered = sorted(skill_scores, key=lambda s: skill_scores[s])
        avg = sum(skill_scores.values()) / len(skill_scores)
        difficulty = _difficulty_for(avg)
        weakest = skills_ordered[0]
        weak_desc = (
            f"最も伸びしろのある「{_SKILL_LABELS[weakest]}」"
            f"（{skill_scores[weakest]:.0f}点）を重点的に強化するメニューです。"
        )

    # 弱点上位から時間内でドリルを詰める
    exercises: list[dict] = []
    total = 0
    for skill in skills_ordered:
        for drill in _DRILL_LIBRARY[skill]:
            if total + drill["duration_min"] > target_duration_min:
                continue
            exercises.append({**drill, "target_skill": skill})
            total += drill["duration_min"]
        if total >= target_duration_min:
            break

    # 1 つも入らなかった場合は最弱スキルの先頭ドリルを必ず入れる
    if not exercises:
        skill = skills_ordered[0]
        drill = _DRILL_LIBRARY[skill][0]
        exercises.append({**drill, "target_skill": skill})
        total = drill["duration_min"]

    menu = TrainingMenu(
        id=uuid.uuid4(),
        athlete_id=profile.id,
        title="AIおすすめ練習メニュー",
        description=weak_desc + " ※スコアは参考値です。",
        is_ai_generated=True,
        total_duration_min=total,
        difficulty=difficulty,
        exercises=exercises,
    )
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


def list_menus(db: Session, user: User, limit: int = 20, offset: int = 0) -> list[TrainingMenu]:
    """自分の練習メニュー一覧を取得する（新しい順）。"""
    profile = _get_profile(db, user)
    stmt = (
        select(TrainingMenu)
        .where(TrainingMenu.athlete_id == profile.id)
        .order_by(TrainingMenu.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all())


def get_menu(db: Session, user: User, menu_id: uuid.UUID) -> TrainingMenu:
    """練習メニューを 1 件取得する（本人のみ）。"""
    profile = _get_profile(db, user)
    menu = db.get(TrainingMenu, menu_id)
    if menu is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メニューが見つかりません",
        )
    if menu.athlete_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このメニューへのアクセス権限がありません",
        )
    return menu


def delete_menu(db: Session, user: User, menu_id: uuid.UUID) -> None:
    """練習メニューを削除する（本人のみ）。"""
    menu = get_menu(db, user, menu_id)
    db.delete(menu)
    db.commit()
