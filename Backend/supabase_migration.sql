-- ==============================================================================
-- CiteFlow Complete PostgreSQL Schema Migration for Supabase
-- ==============================================================================
-- Paste and run this script directly in your Supabase Dashboard:
-- Supabase Dashboard -> SQL Editor -> New Query -> Paste -> Run
-- ==============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 1. Users Table
-- ==============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_lower_email 
    ON users (lower(email));

-- ==============================================================================
-- 2. Refresh Tokens Table (Authentication Session Management)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    family_id UUID NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id 
    ON refresh_tokens (user_id);

-- ==============================================================================
-- 3. Folders Table (Hierarchical Library Organization)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID NULL REFERENCES folders(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_folders_owner_parent 
    ON folders (owner_id, parent_id);

-- Enforce unique folder name per parent directory
CREATE UNIQUE INDEX IF NOT EXISTS uq_folders_owner_parent_lower_name 
    ON folders (owner_id, parent_id, lower(name)) 
    WHERE parent_id IS NOT NULL;

-- Enforce single root folder per user
CREATE UNIQUE INDEX IF NOT EXISTS uq_folders_owner_root_only 
    ON folders (owner_id) 
    WHERE parent_id IS NULL;

-- ==============================================================================
-- 4. Files Table (PDF Document Metadata & ImageKit References)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    folder_id UUID NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    ext TEXT NOT NULL,
    mime TEXT NULL,
    size_bytes BIGINT NOT NULL,
    sha256 TEXT NOT NULL,
    imagekit_file_id TEXT NOT NULL,
    imagekit_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_files_owner_folder 
    ON files (owner_id, folder_id);

-- Enforce unique file name per folder
CREATE UNIQUE INDEX IF NOT EXISTS uq_files_folder_lower_name 
    ON files (folder_id, lower(name));

-- ==============================================================================
-- 5. Storage Deletions Table (Background Asynchronous Cleanup)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS storage_deletions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    imagekit_file_id TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==============================================================================
-- 6. Citation Styles Table (Custom & Built-in Citation Formats)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS citation_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    template TEXT NOT NULL,
    is_builtin BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_citation_styles_owner_id 
    ON citation_styles (owner_id);

CREATE INDEX IF NOT EXISTS ix_citation_styles_slug 
    ON citation_styles (slug);

-- Seed System Built-in Citation Styles (IOP, AMA/Vancouver, IEEE)
INSERT INTO citation_styles (id, owner_id, name, slug, template, is_builtin, created_at, updated_at)
VALUES 
    (
        '00000000-0000-0000-0000-000000000001',
        NULL,
        'IOP',
        'iop-default',
        $$\bibitem{citation key} authors year \textit{journal abbreviation} \href{doi url}{\textbf{volume} locator}.$$,
        true,
        NOW(),
        NOW()
    ),
    (
        '00000000-0000-0000-0000-000000000002',
        NULL,
        'AMA / Vancouver',
        'ama-vancouver',
        $$\bibitem{citation key} authors last first . title. journal abbreviation year;volume(issue):article number. doi:doi.$$,
        true,
        NOW(),
        NOW()
    ),
    (
        '00000000-0000-0000-0000-000000000003',
        NULL,
        'IEEE',
        'ieee',
        $$\bibitem{citation key} authors first. last, ``title,'' \textit{journal}, vol. volume, no. issue, Article article number, year. \href{doi url}{doi url}$$,
        true,
        NOW(),
        NOW()
    )
ON CONFLICT (id) DO UPDATE 
SET 
    name = EXCLUDED.name,
    template = EXCLUDED.template,
    slug = EXCLUDED.slug,
    is_builtin = EXCLUDED.is_builtin,
    updated_at = NOW();

-- ==============================================================================
-- 7. Citation Jobs Table (Background Citation Extraction Pipeline)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    style_id UUID NULL REFERENCES citation_styles(id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    tex_mode VARCHAR(20) NOT NULL DEFAULT 'standalone',
    pending_interrupt JSONB NULL,
    result_tex TEXT NULL,
    result_metadata JSONB NULL,
    reasons JSONB NULL,
    error_code VARCHAR(50) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_jobs_owner_created 
    ON jobs (owner_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_jobs_file_id 
    ON jobs (file_id);

CREATE INDEX IF NOT EXISTS ix_jobs_style_id 
    ON jobs (style_id);

-- Enforce only one active job per file at a time
CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_file_active 
    ON jobs (file_id) 
    WHERE status IN ('queued', 'running', 'needs_title_confirmation', 'needs_review');

-- ==============================================================================
-- 8. Alembic Migration Tracking Table
-- ==============================================================================
-- This records that Alembic is synced to the latest migration head (0004).
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) PRIMARY KEY
);

INSERT INTO alembic_version (version_num) 
VALUES ('0004_fix_citation_styles_schema')
ON CONFLICT (version_num) DO NOTHING;

