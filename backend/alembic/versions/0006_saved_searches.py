"""saved_searches テーブルを追加 (C#23)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scout_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("position", sa.String(50), nullable=True),
        sa.Column("sport", sa.String(50), nullable=True),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("min_total_score", sa.Float(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["scout_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_saved_searches_scout_user_id", "saved_searches", ["scout_user_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_searches_scout_user_id", table_name="saved_searches")
    op.drop_table("saved_searches")
