"""Part B Citation Jobs table

Revision ID: 0002_part_b_jobs
Revises: 0001_part_a_tables
Create Date: 2026-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0002_part_b_jobs"
down_revision: Union[str, None] = "0001_part_a_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="queued", nullable=False),
        sa.Column("tex_mode", sa.String(length=20), server_default="standalone", nullable=False),
        sa.Column("pending_interrupt", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_tex", sa.Text(), nullable=True),
        sa.Column("result_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_jobs_owner_created",
        "jobs",
        ["owner_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_jobs_file_id", "jobs", ["file_id"])
    op.create_index(
        "uq_jobs_file_active",
        "jobs",
        ["file_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running', 'needs_title_confirmation', 'needs_review')"),
    )


def downgrade() -> None:
    op.drop_index("uq_jobs_file_active", table_name="jobs")
    op.drop_index("ix_jobs_file_id", table_name="jobs")
    op.drop_index("ix_jobs_owner_created", table_name="jobs")
    op.drop_table("jobs")
