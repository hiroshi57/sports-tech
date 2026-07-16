"""スカウトCRM系テーブルを追加 (C#25-27, C#30)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-16 00:00:00.000000

contact_logs / athlete_notes / video_clips / profile_view_logs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    contact_stage = sa.Enum(
        "INTERESTED", "CONTACTED", "TRIAL", "OFFER", "SIGNED", "DROPPED", name="contact_stage"
    )

    op.create_table(
        "contact_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scout_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("athlete_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", contact_stage, nullable=False, server_default="INTERESTED"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["scout_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["athlete_profile_id"], ["athlete_profiles.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_contact_logs_scout_user_id", "contact_logs", ["scout_user_id"])
    op.create_index("ix_contact_logs_athlete_profile_id", "contact_logs", ["athlete_profile_id"])

    op.create_table(
        "athlete_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("athlete_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["athlete_profile_id"], ["athlete_profiles.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_athlete_notes_author_user_id", "athlete_notes", ["author_user_id"])
    op.create_index("ix_athlete_notes_athlete_profile_id", "athlete_notes", ["athlete_profile_id"])

    op.create_table(
        "video_clips",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creator_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("start_sec", sa.Float(), nullable=False),
        sa.Column("end_sec", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_video_clips_video_id", "video_clips", ["video_id"])
    op.create_index("ix_video_clips_creator_user_id", "video_clips", ["creator_user_id"])

    op.create_table(
        "profile_view_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("viewer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("athlete_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["viewer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["athlete_profile_id"], ["athlete_profiles.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_profile_view_logs_viewer_user_id", "profile_view_logs", ["viewer_user_id"])
    op.create_index(
        "ix_profile_view_logs_athlete_profile_id", "profile_view_logs", ["athlete_profile_id"]
    )


def downgrade() -> None:
    for table in ("profile_view_logs", "video_clips", "athlete_notes", "contact_logs"):
        op.drop_table(table)
    sa.Enum(name="contact_stage").drop(op.get_bind(), checkfirst=True)
