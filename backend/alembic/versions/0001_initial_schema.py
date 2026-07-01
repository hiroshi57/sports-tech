"""initial schema — 7 tables: users, athlete_profiles, videos, analysis_results,
activity_logs, self_care_records, training_menus

Revision ID: 0001
Revises:
Create Date: 2026-07-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── ENUM 型の作成 ──────────────────────────────────────────────
    user_role = postgresql.ENUM("athlete", "scout", "coach", name="user_role", create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)

    video_status = postgresql.ENUM(
        "pending", "processing", "completed", "failed", name="video_status", create_type=False
    )
    video_status.create(op.get_bind(), checkfirst=True)

    activity_type = postgresql.ENUM(
        "practice", "match", "rest", name="activity_type", create_type=False
    )
    activity_type.create(op.get_bind(), checkfirst=True)

    # ── users ──────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("athlete", "scout", "coach", name="user_role"),
            nullable=False,
            server_default="athlete",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("birth_date", sa.Date, nullable=True),
        sa.Column("parental_consent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── athlete_profiles ───────────────────────────────────────────
    op.create_table(
        "athlete_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("position", sa.String(50), nullable=True),
        sa.Column("sport", sa.String(50), nullable=False, server_default="football"),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("height_cm", sa.Float, nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_athlete_profiles_user_id", "athlete_profiles", ["user_id"], unique=True)

    # ── videos ─────────────────────────────────────────────────────
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "athlete_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("duration_sec", sa.Integer, nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("mime_type", sa.String(50), nullable=False, server_default="video/mp4"),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "completed", "failed", name="video_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_videos_athlete_id", "videos", ["athlete_id"])
    op.create_index("ix_videos_status", "videos", ["status"])
    op.create_index("ix_videos_s3_key", "videos", ["s3_key"], unique=True)

    # ── analysis_results ───────────────────────────────────────────
    op.create_table(
        "analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sprint_score", sa.Float, nullable=False),
        sa.Column("ball_control_score", sa.Float, nullable=False),
        sa.Column("positioning_score", sa.Float, nullable=False),
        sa.Column("body_usage_score", sa.Float, nullable=False),
        sa.Column("total_score", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("sprint_score BETWEEN 0 AND 100", name="ck_sprint_score_range"),
        sa.CheckConstraint(
            "ball_control_score BETWEEN 0 AND 100", name="ck_ball_control_score_range"
        ),
        sa.CheckConstraint(
            "positioning_score BETWEEN 0 AND 100", name="ck_positioning_score_range"
        ),
        sa.CheckConstraint("body_usage_score BETWEEN 0 AND 100", name="ck_body_usage_score_range"),
        sa.CheckConstraint("total_score BETWEEN 0 AND 100", name="ck_total_score_range"),
    )
    op.create_index("ix_analysis_results_video_id", "analysis_results", ["video_id"], unique=True)

    # ── activity_logs ──────────────────────────────────────────────
    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "athlete_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activity_date", sa.Date, nullable=False),
        sa.Column(
            "activity_type",
            sa.Enum("practice", "match", "rest", name="activity_type"),
            nullable=False,
        ),
        sa.Column("duration_min", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fatigue_level", sa.Integer, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("fatigue_level BETWEEN 1 AND 5", name="ck_fatigue_level_range"),
        sa.CheckConstraint("duration_min >= 0", name="ck_duration_min_positive"),
    )
    op.create_index("ix_activity_logs_athlete_id", "activity_logs", ["athlete_id"])
    op.create_index("ix_activity_logs_date", "activity_logs", ["activity_date"])

    # ── self_care_records ──────────────────────────────────────────
    op.create_table(
        "self_care_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "athlete_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("record_date", sa.Date, nullable=False),
        sa.Column("sleep_hours", sa.Float, nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("nutrition_notes", sa.Text, nullable=True),
        sa.Column("injury_risk_score", sa.Float, nullable=True),
        sa.Column("alert_sent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("sleep_hours BETWEEN 0 AND 24", name="ck_sleep_hours_range"),
        sa.CheckConstraint("injury_risk_score BETWEEN 0 AND 100", name="ck_injury_risk_range"),
    )
    op.create_index("ix_self_care_records_athlete_id", "self_care_records", ["athlete_id"])
    op.create_index("ix_self_care_records_date", "self_care_records", ["record_date"])

    # ── training_menus ─────────────────────────────────────────────
    op.create_table(
        "training_menus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "athlete_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("athlete_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_ai_generated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("total_duration_min", sa.Integer, nullable=False, server_default="0"),
        sa.Column("difficulty", sa.String(20), nullable=False, server_default="intermediate"),
        sa.Column("exercises", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_training_menus_athlete_id", "training_menus", ["athlete_id"])


def downgrade() -> None:
    op.drop_table("training_menus")
    op.drop_table("self_care_records")
    op.drop_table("activity_logs")
    op.drop_table("analysis_results")
    op.drop_table("videos")
    op.drop_table("athlete_profiles")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS activity_type")
    op.execute("DROP TYPE IF EXISTS video_status")
    op.execute("DROP TYPE IF EXISTS user_role")
