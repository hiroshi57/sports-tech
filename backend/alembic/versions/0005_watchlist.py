"""watchlist_items テーブルを追加 (C#22)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scout_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("tags", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["scout_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["athlete_id"], ["athlete_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("scout_user_id", "athlete_id", name="uq_watchlist_scout_athlete"),
    )
    op.create_index("ix_watchlist_scout_user_id", "watchlist_items", ["scout_user_id"])
    op.create_index("ix_watchlist_athlete_id", "watchlist_items", ["athlete_id"])


def downgrade() -> None:
    op.drop_index("ix_watchlist_athlete_id", table_name="watchlist_items")
    op.drop_index("ix_watchlist_scout_user_id", table_name="watchlist_items")
    op.drop_table("watchlist_items")
