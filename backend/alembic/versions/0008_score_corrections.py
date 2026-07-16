"""score_corrections テーブルを追加 (A#9 補正ループ)

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    correction_status = sa.Enum("PENDING", "APPROVED", "REJECTED", name="correction_status")

    op.create_table(
        "score_corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("suggested_value", sa.Float(), nullable=True),
        sa.Column("status", correction_status, nullable=False, server_default="PENDING"),
        sa.Column("resolved_value", sa.Float(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["analysis_result_id"], ["analysis_results.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_score_corrections_analysis_result_id",
        "score_corrections",
        ["analysis_result_id"],
    )
    op.create_index(
        "ix_score_corrections_reporter_user_id",
        "score_corrections",
        ["reporter_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_score_corrections_reporter_user_id", table_name="score_corrections")
    op.drop_index("ix_score_corrections_analysis_result_id", table_name="score_corrections")
    op.drop_table("score_corrections")
    sa.Enum(name="correction_status").drop(op.get_bind(), checkfirst=True)
