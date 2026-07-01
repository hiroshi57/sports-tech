"""モデル定義の単体テスト（DB接続不要）。

SQLAlchemy の in-memory SQLite を使いモデルのCRUDを検証する。
本番は PostgreSQL だが、スキーマ整合性・制約の検証は SQLite で行う。
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models import (
    ActivityLog,
    ActivityType,
    AnalysisResult,
    AthleteProfile,
    Base,
    TrainingMenu,
    User,
    UserRole,
    Video,
    VideoStatus,
)

# ── フィクスチャ ────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def engine():
    """インメモリ SQLite エンジン（テスト用）。"""
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # SQLite は CHECK 制約を無効化しているため手動で有効化
    @event.listens_for(_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[misc]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)


@pytest.fixture
def session(engine):
    """各テスト用のセッション（テスト後にすべての変更を削除してリセット）。"""
    _session = Session(engine)
    yield _session
    _session.rollback()
    _session.close()


def make_user(session: Session, role: UserRole = UserRole.ATHLETE) -> User:
    """テスト用 User を作成して返す。"""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        role=role,
        is_active=True,
        parental_consent=False,
    )
    session.add(user)
    session.flush()
    return user


def make_athlete_profile(session: Session, user: User) -> AthleteProfile:
    """テスト用 AthleteProfile を作成して返す。"""
    profile = AthleteProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        name="テスト選手",
        position="FW",
        sport="football",
        is_public=True,
    )
    session.add(profile)
    session.flush()
    return profile


# ── User テスト ─────────────────────────────────────────────────────


class TestUser:
    def test_create_athlete(self, session: Session) -> None:
        """選手ロールのユーザーが作成できる。"""
        user = make_user(session, UserRole.ATHLETE)
        assert user.id is not None
        assert user.role == UserRole.ATHLETE
        assert user.is_active is True

    def test_create_scout(self, session: Session) -> None:
        """スカウトロールのユーザーが作成できる。"""
        user = make_user(session, UserRole.SCOUT)
        assert user.role == UserRole.SCOUT

    def test_email_is_unique(self, session: Session) -> None:
        """同じメールアドレスは登録できない。"""
        email = "unique@example.com"
        session.add(User(id=uuid.uuid4(), email=email, role=UserRole.ATHLETE))
        session.flush()
        session.add(User(id=uuid.uuid4(), email=email, role=UserRole.ATHLETE))
        with pytest.raises(Exception):
            session.flush()


# ── AthleteProfile テスト ───────────────────────────────────────────


class TestAthleteProfile:
    def test_create_profile(self, session: Session) -> None:
        """選手プロフィールが作成できる。"""
        user = make_user(session)
        profile = make_athlete_profile(session, user)
        assert profile.id is not None
        assert profile.name == "テスト選手"
        assert profile.is_public is True

    def test_cascade_delete(self, session: Session) -> None:
        """User 削除時に AthleteProfile も削除される。"""
        user = make_user(session)
        profile = make_athlete_profile(session, user)
        profile_id = profile.id

        session.delete(user)
        session.flush()

        result = session.get(AthleteProfile, profile_id)
        assert result is None


# ── Video テスト ────────────────────────────────────────────────────


class TestVideo:
    def test_create_video(self, session: Session) -> None:
        """動画レコードが作成できる。"""
        user = make_user(session)
        profile = make_athlete_profile(session, user)

        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            s3_key=f"videos/{profile.id}/test.mp4",
            status=VideoStatus.PENDING,
            mime_type="video/mp4",
        )
        session.add(video)
        session.flush()

        assert video.id is not None
        assert video.status == VideoStatus.PENDING

    def test_status_transitions(self, session: Session) -> None:
        """ステータスが正しく遷移できる。"""
        user = make_user(session)
        profile = make_athlete_profile(session, user)

        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            s3_key=f"videos/{profile.id}/test2.mp4",
            status=VideoStatus.PENDING,
        )
        session.add(video)
        session.flush()

        video.status = VideoStatus.PROCESSING
        session.flush()
        assert video.status == VideoStatus.PROCESSING

        video.status = VideoStatus.COMPLETED
        session.flush()
        assert video.status == VideoStatus.COMPLETED


# ── AnalysisResult テスト ───────────────────────────────────────────


class TestAnalysisResult:
    def _make_video(self, session: Session) -> Video:
        user = make_user(session)
        profile = make_athlete_profile(session, user)
        video = Video(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            s3_key=f"videos/{profile.id}/{uuid.uuid4().hex}.mp4",
            status=VideoStatus.COMPLETED,
        )
        session.add(video)
        session.flush()
        return video

    def test_create_analysis_result(self, session: Session) -> None:
        """分析結果が正しく作成できる。"""
        video = self._make_video(session)
        result = AnalysisResult(
            id=uuid.uuid4(),
            video_id=video.id,
            sprint_score=75.0,
            ball_control_score=68.5,
            positioning_score=82.0,
            body_usage_score=70.0,
            total_score=73.9,
            confidence=0.92,
        )
        session.add(result)
        session.flush()

        assert result.id is not None
        assert result.total_score == 73.9
        assert result.confidence == 0.92

    def test_score_boundary_values(self, session: Session) -> None:
        """スコアの境界値（0と100）が保存できる。"""
        video = self._make_video(session)
        result = AnalysisResult(
            id=uuid.uuid4(),
            video_id=video.id,
            sprint_score=0.0,
            ball_control_score=100.0,
            positioning_score=50.0,
            body_usage_score=50.0,
            total_score=50.0,
        )
        session.add(result)
        session.flush()
        assert result.sprint_score == 0.0
        assert result.ball_control_score == 100.0


# ── ActivityLog テスト ──────────────────────────────────────────────


class TestActivityLog:
    def test_create_activity_log(self, session: Session) -> None:
        """活動記録が作成できる。"""
        user = make_user(session)
        profile = make_athlete_profile(session, user)

        log = ActivityLog(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            activity_date=date(2026, 7, 1),
            activity_type=ActivityType.PRACTICE,
            duration_min=90,
            fatigue_level=3,
            notes="通常練習",
        )
        session.add(log)
        session.flush()

        assert log.id is not None
        assert log.fatigue_level == 3
        assert log.activity_type == ActivityType.PRACTICE


# ── TrainingMenu テスト ─────────────────────────────────────────────


class TestTrainingMenu:
    def test_create_training_menu(self, session: Session) -> None:
        """練習メニューが作成できる（JSON exercises 含む）。"""
        user = make_user(session)
        profile = make_athlete_profile(session, user)

        exercises = [
            {"name": "コーンドリブル", "duration_min": 15, "description": "ジグザグ走"},
            {"name": "シュート練習", "duration_min": 20, "description": "ゴール前から10本"},
        ]

        menu = TrainingMenu(
            id=uuid.uuid4(),
            athlete_id=profile.id,
            title="スプリント強化メニュー",
            is_ai_generated=True,
            total_duration_min=45,
            difficulty="intermediate",
            exercises=exercises,
        )
        session.add(menu)
        session.flush()

        assert menu.id is not None
        assert len(menu.exercises) == 2
        assert menu.exercises[0]["name"] == "コーンドリブル"
        assert menu.is_ai_generated is True


# ── Pydantic スキーマ テスト ────────────────────────────────────────


class TestSchemas:
    def test_analysis_score_clamp(self) -> None:
        """スコアが 0〜100 の範囲に正しくクランプされる。"""
        from app.schemas.video import AnalysisScoreSchema

        score = AnalysisScoreSchema(
            sprint_score=50.0,
            ball_control_score=100.0,
            positioning_score=0.0,
            body_usage_score=75.0,
            total_score=56.25,
        )
        assert score.sprint_score == 50.0
        assert score.ball_control_score == 100.0
        assert score.positioning_score == 0.0

    def test_analysis_score_out_of_range(self) -> None:
        """101 点や -1 点は ValidationError になる。"""
        from pydantic import ValidationError

        from app.schemas.video import AnalysisScoreSchema

        with pytest.raises(ValidationError):
            AnalysisScoreSchema(
                sprint_score=101.0,
                ball_control_score=50.0,
                positioning_score=50.0,
                body_usage_score=50.0,
                total_score=50.0,
            )

        with pytest.raises(ValidationError):
            AnalysisScoreSchema(
                sprint_score=-1.0,
                ball_control_score=50.0,
                positioning_score=50.0,
                body_usage_score=50.0,
                total_score=50.0,
            )

    def test_user_minor_requires_consent(self) -> None:
        """未成年者（birth_date が 18歳未満）は parental_consent=True が必要。"""
        from pydantic import ValidationError

        from app.schemas.user import UserCreate

        # 未成年者で consent=False → エラー
        with pytest.raises(ValidationError):
            UserCreate(
                email="minor@example.com",
                birth_date=date(2015, 1, 1),
                parental_consent=False,
            )

        # 未成年者で consent=True → OK
        user = UserCreate(
            email="minor-ok@example.com",
            birth_date=date(2015, 1, 1),
            parental_consent=True,
        )
        assert user.parental_consent is True

    def test_athlete_profile_create_validation(self) -> None:
        """身長・体重のバリデーションが機能する。"""
        from pydantic import ValidationError

        from app.schemas.athlete import AthleteProfileCreate

        # 正常値
        profile = AthleteProfileCreate(name="田中太郎", height_cm=175.0, weight_kg=68.0)
        assert profile.name == "田中太郎"

        # 不正値（身長 0 以下）
        with pytest.raises(ValidationError):
            AthleteProfileCreate(name="田中太郎", height_cm=0.0)
