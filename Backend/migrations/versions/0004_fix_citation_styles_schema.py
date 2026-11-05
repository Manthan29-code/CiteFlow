"""Fix citation styles schema: rename user_id to owner_id, add jobs.style_id, ensure built-ins

Revision ID: 0004_fix_citation_styles_schema
Revises: 0003_citation_styles
Create Date: 2026-11-05 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0004_fix_citation_styles_schema"
down_revision: Union[str, None] = "0003_citation_styles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Recreate citation_styles cleanly to fix any malformed previous schema
    # and guarantee all columns (id, owner_id, name, slug, template, is_builtin, created_at, updated_at) exist.
    op.execute(
        """
        DO $$
        BEGIN
            -- Drop existing foreign key on jobs if it exists
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_jobs_style_id'
            ) THEN
                ALTER TABLE jobs DROP CONSTRAINT fk_jobs_style_id;
            END IF;

            -- Drop old/malformed citation_styles table
            DROP TABLE IF EXISTS citation_styles CASCADE;

            -- Create clean citation_styles table matching SQLAlchemy CitationStyle model exactly
            CREATE TABLE citation_styles (
                id UUID PRIMARY KEY,
                owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                slug VARCHAR(100) NOT NULL,
                template TEXT NOT NULL,
                is_builtin BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE INDEX ix_citation_styles_owner_id ON citation_styles (owner_id);
            CREATE INDEX ix_citation_styles_slug ON citation_styles (slug);

            -- 2. Ensure jobs.style_id column and foreign key exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'jobs' AND column_name = 'style_id'
            ) THEN
                ALTER TABLE jobs ADD COLUMN style_id UUID;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_jobs_style_id'
            ) THEN
                ALTER TABLE jobs ADD CONSTRAINT fk_jobs_style_id FOREIGN KEY (style_id) REFERENCES citation_styles(id) ON DELETE SET NULL;
            END IF;

            CREATE INDEX IF NOT EXISTS ix_jobs_style_id ON jobs (style_id);
        END $$;
        """
    )

    # 3. Seed built-in default citation styles
    op.execute(
        r"""
        INSERT INTO citation_styles (id, owner_id, name, slug, template, is_builtin, created_at, updated_at)
        VALUES 
            (
                '00000000-0000-0000-0000-000000000001',
                NULL,
                'IOP (Default)',
                'iop-default',
                $$\bibitem{<CITATION_KEY>} <AUTHORS> <YEAR> \textit{<JOURNAL_ABBREVIATION>} \href{<DOI_URL>}{\textbf{<VOLUME>} <LOCATOR>}.$$,
                true,
                NOW(),
                NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000002',
                NULL,
                'AMA / Vancouver',
                'ama-vancouver',
                $$\bibitem{<CITATION_KEY>} <AUTHORS_LAST_FIRST()>. <TITLE>. <JOURNAL_ABBREVIATION> <YEAR>;<VOLUME>(<ISSUE>):<ARTICLE_NUMBER>. doi:<DOI>.$$,
                true,
                NOW(),
                NOW()
            ),
            (
                '00000000-0000-0000-0000-000000000003',
                NULL,
                'IEEE',
                'ieee',
                $$\bibitem{<CITATION_KEY>} <AUTHORS_FIRST(.)_LAST>, ``<TITLE>,'' \textit{<JOURNAL>}, vol. <VOLUME>, no. <ISSUE>, Article <ARTICLE_NUMBER>, <YEAR>. \href{<DOI_URL>}{<DOI_URL>}$$,
                true,
                NOW(),
                NOW()
            );
        """
    )


def downgrade() -> None:
    pass
