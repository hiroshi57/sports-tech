"""practice_reviews テーブルを追加 (#12)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "practice_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("self_rating", sa.Integer(), nullable=True),
        sa.Column("went_well", sa.Text(), nullable=True),
        sa.Column("to_improve", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["athlete_id"], ["athlete_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_practice_reviews_athlete_id", "practice_reviews", ["athlete_id"])
    op.create_index("ix_practice_reviews_video_id", "practice_reviews", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_practice_reviews_video_id", table_name="practice_reviews")
    op.drop_index("ix_practice_reviews_athlete_id", table_name="practice_reviews")
    op.drop_table("practice_reviews")
