"""Add user-owned custom citation styles.

Revision ID: 0003_citation_styles
Revises: 0002_part_b_jobs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_citation_styles"
down_revision: Union[str, None] = "0002_part_b_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "citation_styles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("style_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("sample_string", sa.Text(), nullable=False),
        sa.Column("formatting_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "style_name", name="uq_citation_styles_user_name"),
    )
    op.create_index(
        "ix_citation_styles_user_created", "citation_styles",
        ["user_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("is_active IS TRUE"),
    )
    op.create_index(
        "ix_citation_styles_name_trgm", "citation_styles", ["style_name"],
        postgresql_using="gin", postgresql_ops={"style_name": "gin_trgm_ops"},
        postgresql_where=sa.text("is_active IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index("ix_citation_styles_name_trgm", table_name="citation_styles")
    op.drop_index("ix_citation_styles_user_created", table_name="citation_styles")
    op.drop_table("citation_styles")
