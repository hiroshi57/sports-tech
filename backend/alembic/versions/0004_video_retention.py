"""videos に保存期間管理カラムを追加 (D#35)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "videos",
        sa.Column(
            "retention_warned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # 既存行の last_accessed_at を作成日時で初期化
    op.execute("UPDATE videos SET last_accessed_at = created_at WHERE last_accessed_at IS NULL")


def downgrade() -> None:
    op.drop_column("videos", "retention_warned")
    op.drop_column("videos", "last_accessed_at")
