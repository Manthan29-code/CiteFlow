from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFoundError
from app.db.models.deletion import StorageDeletion
from app.db.models.file import File
from app.files.schemas import SignedUrlResponse
from app.storage.base import StorageBackend
from app.storage.cleaner import wake_cleaner


class FileService:
    @staticmethod
    async def get_file(db: AsyncSession, owner_id: UUID, file_id: UUID) -> File:
        """Retrieves a file owned by the user or raises 404."""
        stmt = select(File).where(File.id == file_id, File.owner_id == owner_id)
        result = await db.execute(stmt)
        file = result.scalar_one_or_none()
        if not file:
            raise NotFoundError("File not found.")
        return file

    @classmethod
    async def get_signed_url(
        cls, db: AsyncSession, storage: StorageBackend, owner_id: UUID, file_id: UUID
    ) -> SignedUrlResponse:
        """Generates a short-lived signed URL for viewing the PDF."""
        file = await cls.get_file(db, owner_id, file_id)
        url = await storage.signed_url(
            file.imagekit_path,
            expires_in=settings.SIGNED_URL_EXPIRES_SECONDS,
        )
        return SignedUrlResponse(
            url=url,
            expires_in=settings.SIGNED_URL_EXPIRES_SECONDS,
        )

    @classmethod
    async def delete_file(
        cls, db: AsyncSession, owner_id: UUID, file_id: UUID
    ) -> None:
        """
        Deletes a single file.
        In one transaction:
        1. Checks ownership.
        2. Cancels any active jobs for this file.
        3. Enqueues imagekit_file_id into storage_deletions.
        4. Deletes database row (cascade deletes job rows).
        5. Commits and wakes storage cleaner.
        """
        file = await cls.get_file(db, owner_id, file_id)

        # Cancel active in-memory tasks for jobs of this file
        from app.db.models.job import Job
        from app.jobs.runner import cancel_running_task
        jobs_stmt = select(Job.id).where(Job.file_id == file_id)
        job_ids = (await db.execute(jobs_stmt)).scalars().all()
        for jid in job_ids:
            cancel_running_task(jid)

        db.add(StorageDeletion(imagekit_file_id=file.imagekit_file_id))
        await db.delete(file)
        await db.commit()

        wake_cleaner()

