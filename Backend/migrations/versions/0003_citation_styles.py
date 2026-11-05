"""Citation Styles table and jobs style_id link

Revision ID: 0003_citation_styles
Revises: 0002_part_b_jobs
Create Date: 2026-11-05 09:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_citation_styles"
down_revision: Union[str, None] = "0002_part_b_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create citation_styles table
    styles_table = op.create_table(
        "citation_styles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_citation_styles_owner_id", "citation_styles", ["owner_id"])
    op.create_index("ix_citation_styles_slug", "citation_styles", ["slug"])

    # 2. Add style_id to jobs table
    op.add_column("jobs", sa.Column("style_id", sa.Uuid(), nullable=True))
    op.create_index("ix_jobs_style_id", "jobs", ["style_id"])
    op.create_foreign_key(
        "fk_jobs_style_id",
        "jobs",
        "citation_styles",
        ["style_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. Seed built-in default styles
    op.bulk_insert(
        styles_table,
        [
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
                "owner_id": None,
                "name": "IOP (Default)",
                "slug": "iop-default",
                "template": r"\bibitem{<CITATION_KEY>} <AUTHORS> <YEAR> \textit{<JOURNAL_ABBREVIATION>} \href{<DOI_URL>}{\textbf{<VOLUME>} <LOCATOR>}.",
                "is_builtin": True,
            },
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
                "owner_id": None,
                "name": "AMA / Vancouver",
                "slug": "ama-vancouver",
                "template": r"\bibitem{<CITATION_KEY>} <AUTHORS_LAST_FIRST()>. <TITLE>. <JOURNAL_ABBREVIATION> <YEAR>;<VOLUME>(<ISSUE>):<ARTICLE_NUMBER>. doi:<DOI>.",
                "is_builtin": True,
            },
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
                "owner_id": None,
                "name": "IEEE",
                "slug": "ieee",
                "template": r"\bibitem{<CITATION_KEY>} <AUTHORS_FIRST(.)_LAST>, ``<TITLE>,'' \textit{<JOURNAL>}, vol. <VOLUME>, no. <ISSUE>, Article <ARTICLE_NUMBER>, <YEAR>. \href{<DOI_URL>}{<DOI_URL>}",
                "is_builtin": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_constraint("fk_jobs_style_id", "jobs", type_="foreignkey")
    op.drop_index("ix_jobs_style_id", table_name="jobs")
    op.drop_column("jobs", "style_id")
    op.drop_index("ix_citation_styles_slug", table_name="citation_styles")
    op.drop_index("ix_citation_styles_owner_id", table_name="citation_styles")
    op.drop_table("citation_styles")

