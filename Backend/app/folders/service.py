import unicodedata
from uuid import UUID
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    AppError,
    FolderTooDeepError,
    NameConflictError,
    NotFoundError,
    RootFolderProtectedError,
)
from app.db.models.deletion import StorageDeletion
from app.db.models.file import File
from app.db.models.folder import Folder
from app.folders.schemas import Breadcrumb, FileSummary, FolderDetailResponse, FolderSummary
from app.storage.cleaner import wake_cleaner


def validate_and_sanitize_folder_name(name: str) -> str:
    """Validates and normalizes folder name according to Section 2.6."""
    if not name:
        raise AppError(422, "invalid_name", "Folder name cannot be empty.")

    # Unicode normalization to NFC
    normalized = unicodedata.normalize("NFC", name)
    cleaned = normalized.strip()

    if not cleaned:
        raise AppError(422, "invalid_name", "Folder name cannot consist only of whitespace.")

    if len(cleaned) > settings.MAX_NAME_LENGTH:
        raise AppError(
            422,
            "invalid_name",
            f"Folder name exceeds maximum length of {settings.MAX_NAME_LENGTH} characters.",
        )

    # Disallowed characters: /, \, NUL, control chars
    for ch in cleaned:
        if ch in ("/", "\\", "\0") or unicodedata.category(ch).startswith("C"):
            raise AppError(422, "invalid_name", "Folder name contains illegal characters.")

    # Reject . and ..
    if cleaned in (".", ".."):
        raise AppError(422, "invalid_name", "Folder name cannot be '.' or '..'.")

    # Reject trailing dots/spaces
    if cleaned.endswith(".") or cleaned.endswith(" "):
        raise AppError(422, "invalid_name", "Folder name cannot end with a dot or space.")

    return cleaned


class FolderService:
    @staticmethod
    async def get_root_folder(db: AsyncSession, owner_id: UUID) -> Folder:
        """Retrieves the single root folder for the user (parent_id is NULL)."""
        stmt = select(Folder).where(Folder.owner_id == owner_id, Folder.parent_id.is_(None))
        result = await db.execute(stmt)
        root = result.scalar_one_or_none()
        if not root:
            raise NotFoundError("Root folder not found.")
        return root

    @staticmethod
    async def get_folder(db: AsyncSession, owner_id: UUID, folder_id: UUID) -> Folder:
        """Retrieves a folder owned by user or raises 404."""
        stmt = select(Folder).where(Folder.id == folder_id, Folder.owner_id == owner_id)
        result = await db.execute(stmt)
        folder = result.scalar_one_or_none()
        if not folder:
            raise NotFoundError("Folder not found.")
        return folder

    @staticmethod
    async def get_folder_depth(db: AsyncSession, owner_id: UUID, folder_id: UUID) -> int:
        """Calculates depth from root (root is depth 0)."""
        depth = 0
        current_id = folder_id
        while current_id:
            stmt = select(Folder.parent_id).where(Folder.id == current_id, Folder.owner_id == owner_id)
            parent_id = (await db.execute(stmt)).scalar_one_or_none()
            if parent_id is None:
                break
            depth += 1
            current_id = parent_id
            if depth > settings.MAX_FOLDER_DEPTH:
                break
        return depth

    @staticmethod
    async def get_breadcrumbs(db: AsyncSession, owner_id: UUID, folder_id: UUID) -> list[Breadcrumb]:
        """Calculates breadcrumbs from root to current folder."""
        chain: list[Breadcrumb] = []
        current_id: UUID | None = folder_id

        while current_id:
            stmt = select(Folder.id, Folder.name, Folder.parent_id).where(
                Folder.id == current_id, Folder.owner_id == owner_id
            )
            row = (await db.execute(stmt)).first()
            if not row:
                break
            chain.append(Breadcrumb(id=row.id, name=row.name))
            current_id = row.parent_id

        chain.reverse()
        return chain

    @classmethod
    async def create_folder(
        cls, db: AsyncSession, owner_id: UUID, name: str, parent_id: UUID
    ) -> Folder:
        """Creates a subfolder after validating name, depth, and name conflict."""
        cleaned_name = validate_and_sanitize_folder_name(name)

        # Verify parent exists and belongs to owner
        parent = await cls.get_folder(db, owner_id, parent_id)

        # Depth check: parent depth + 1
        parent_depth = await cls.get_folder_depth(db, owner_id, parent.id)
        if parent_depth + 1 > settings.MAX_FOLDER_DEPTH:
            raise FolderTooDeepError(
                f"Cannot create folder. Depth exceeds maximum of {settings.MAX_FOLDER_DEPTH}."
            )

        # Case-insensitive name conflict check
        conflict_stmt = select(Folder).where(
            Folder.owner_id == owner_id,
            Folder.parent_id == parent_id,
            func.lower(Folder.name) == cleaned_name.lower(),
        )
        existing = (await db.execute(conflict_stmt)).scalar_one_or_none()
        if existing:
            raise NameConflictError(f"A folder with name '{cleaned_name}' already exists here.")

        new_folder = Folder(
            owner_id=owner_id,
            parent_id=parent_id,
            name=cleaned_name,
        )
        db.add(new_folder)
        await db.commit()
        await db.refresh(new_folder)
        return new_folder

    @classmethod
    async def get_folder_detail(
        cls,
        db: AsyncSession,
        owner_id: UUID,
        folder_id: UUID,
        limit: int = 200,
        cursor: int = 0,
    ) -> FolderDetailResponse:
        """Returns folder details, breadcrumbs, child folders, and files."""
        folder = await cls.get_folder(db, owner_id, folder_id)
        breadcrumbs = await cls.get_breadcrumbs(db, owner_id, folder.id)

        # Fetch child folders sorted case-insensitively
        folders_stmt = (
            select(Folder)
            .where(Folder.owner_id == owner_id, Folder.parent_id == folder.id)
            .order_by(func.lower(Folder.name).asc())
        )
        folder_rows = (await db.execute(folders_stmt)).scalars().all()

        # Fetch files sorted case-insensitively
        files_stmt = (
            select(File)
            .where(File.owner_id == owner_id, File.folder_id == folder.id)
            .order_by(func.lower(File.name).asc())
        )
        file_rows = (await db.execute(files_stmt)).scalars().all()

        folder_summaries = [FolderSummary.model_validate(f) for f in folder_rows]
        file_summaries = [FileSummary.model_validate(f) for f in file_rows]

        # Basic pagination over total items
        total_items = folder_summaries + file_summaries
        paginated_folders = folder_summaries[:limit]
        remaining_limit = max(0, limit - len(paginated_folders))
        paginated_files = file_summaries[:remaining_limit]

        next_cursor = None
        if len(total_items) > limit:
            next_cursor = str(cursor + limit)

        return FolderDetailResponse(
            folder=FolderSummary.model_validate(folder),
            breadcrumbs=breadcrumbs,
            folders=paginated_folders,
            files=paginated_files,
            next_cursor=next_cursor,
        )

    @classmethod
    async def delete_folder_recursive(
        cls, db: AsyncSession, owner_id: UUID, folder_id: UUID
    ) -> None:
        """
        Recursively deletes a folder.
        In one transaction:
        1. Checks root protection.
        2. Queries all descendant files and inserts their imagekit_file_ids into storage_deletions.
        3. Deletes folder row (database cascades remove all child folders & files).
        4. Commits and wakes storage cleaner.
        """
        folder = await cls.get_folder(db, owner_id, folder_id)
        if folder.parent_id is None:
            raise RootFolderProtectedError("The root folder cannot be deleted.")

        # Recursive CTE to find all descendant folder IDs and their files
        cte_query = text("""
            WITH RECURSIVE subfolders AS (
                SELECT id FROM folders WHERE id = :folder_id AND owner_id = :owner_id
                UNION ALL
                SELECT f.id FROM folders f
                JOIN subfolders s ON f.parent_id = s.id
                WHERE f.owner_id = :owner_id
            )
            SELECT id, imagekit_file_id FROM files
            WHERE folder_id IN (SELECT id FROM subfolders)
              AND owner_id = :owner_id
        """)
        result = await db.execute(cte_query, {"folder_id": folder.id, "owner_id": owner_id})
        rows = result.fetchall()
        file_ids = [row[0] for row in rows]
        imagekit_file_ids = [row[1] for row in rows]

        # Cancel active in-memory tasks for jobs of descendant files
        if file_ids:
            from app.db.models.job import Job
            from app.jobs.runner import cancel_running_task
            jobs_stmt = select(Job.id).where(Job.file_id.in_(file_ids))
            job_ids = (await db.execute(jobs_stmt)).scalars().all()
            for jid in job_ids:
                cancel_running_task(jid)

        # Insert into storage_deletions outbox
        for fid in imagekit_file_ids:
            db.add(StorageDeletion(imagekit_file_id=fid))

        # Delete the folder row (ON DELETE CASCADE handles child folders, files, and jobs)
        await db.delete(folder)
        await db.commit()

        # Signal cleaner
        wake_cleaner()

