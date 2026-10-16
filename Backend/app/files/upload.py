import hashlib
import logging
import os
import shutil
from pathlib import Path
from uuid import UUID, uuid4
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    AppError,
    NameConflictError,
    NotFoundError,
    QuotaExceededError,
    UnsupportedMediaTypeError,
)
from app.db.models.deletion import StorageDeletion
from app.db.models.file import File
from app.db.models.folder import Folder
from app.files.handlers.base import get_handler
from app.folders.service import FolderService, validate_and_sanitize_folder_name
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)


async def handle_file_upload(
    db: AsyncSession,
    storage: StorageBackend,
    owner_id: UUID,
    folder_id: UUID,
    upload: UploadFile,
) -> File:
    """
    Handles file upload workflow:
    1. Verify folder ownership.
    2. Validate file extension and handler availability.
    3. Sanitize display name and check case-insensitive conflict.
    4. Spool to temp directory (mode 0700).
    5. Calculate sha256 and size_bytes.
    6. Check user storage quota.
    7. Validate content via handler.
    8. Upload to ImageKit via StorageBackend.
    9. Insert database row with rollback/compensation on failure.
    10. Cleanup temp files in finally.
    """
    # 1. Folder check
    await FolderService.get_folder(db, owner_id, folder_id)

    # 2. Extension check
    raw_filename = upload.filename or "unnamed.pdf"
    name_parts = raw_filename.rsplit(".", 1)
    if len(name_parts) < 2:
        raise UnsupportedMediaTypeError("Uploaded file has no extension.")

    base_name, ext = name_parts[0], name_parts[1].lower().strip()
    if ext not in settings.allowed_extensions_set:
        raise UnsupportedMediaTypeError(
            f"File extension '.{ext}' is not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )

    handler = get_handler(ext)
    if not handler:
        raise UnsupportedMediaTypeError(f"No handler registered for '.{ext}'.")

    # 3. Sanitize display name
    sanitized_base = validate_and_sanitize_folder_name(base_name)
    display_name = f"{sanitized_base}.{ext}"

    # Check case-insensitive conflict in target folder
    conflict_stmt = select(File).where(
        File.owner_id == owner_id,
        File.folder_id == folder_id,
        func.lower(File.name) == display_name.lower(),
    )
    existing = (await db.execute(conflict_stmt)).scalar_one_or_none()
    if existing:
        raise NameConflictError(f"A file named '{display_name}' already exists in this folder.")

    # 4. Spool to temp directory with mode 0700
    temp_parent = Path(settings.TEMP_DIR)
    temp_dir = temp_parent / str(uuid4())
    temp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    server_filename = f"{uuid4().hex}.{ext}"
    spool_path = temp_dir / server_filename

    sha256_hasher = hashlib.sha256()
    size_bytes = 0

    try:
        with open(spool_path, "wb") as f_out:
            while chunk := await upload.read(64 * 1024):
                size_bytes += len(chunk)
                sha256_hasher.update(chunk)
                f_out.write(chunk)

        file_sha256 = sha256_hasher.hexdigest()

        # 5. Check user quota
        if settings.USER_STORAGE_QUOTA_MB > 0:
            quota_bytes = settings.USER_STORAGE_QUOTA_MB * 1024 * 1024
            sum_stmt = select(func.coalesce(func.sum(File.size_bytes), 0)).where(File.owner_id == owner_id)
            used_bytes = (await db.execute(sum_stmt)).scalar() or 0
            if used_bytes + size_bytes > quota_bytes:
                raise QuotaExceededError(
                    f"Upload would exceed your storage quota of {settings.USER_STORAGE_QUOTA_MB}MB."
                )

        # 6. Validate real content via handler
        await handler.validate(spool_path)

        # 7. Upload to ImageKit
        with open(spool_path, "rb") as f_in:
            stored = await storage.upload(
                file=f_in,
                owner_id=owner_id,
                stored_name=server_filename,
            )

        # 8. Insert database row with compensation on failure
        db_file = File(
            id=uuid4(),
            owner_id=owner_id,
            folder_id=folder_id,
            name=display_name,
            ext=ext,
            mime=upload.content_type,
            size_bytes=size_bytes,
            sha256=file_sha256,
            imagekit_file_id=stored.file_id,
            imagekit_path=stored.file_path,
        )
        db.add(db_file)

        try:
            await db.commit()
            await db.refresh(db_file)
            return db_file
        except Exception as db_exc:
            await db.rollback()
            logger.error(f"Database insert failed after storage upload, compensating: {db_exc}")
            # Compensate: delete uploaded file from ImageKit
            try:
                comp_result = await storage.delete_many([stored.file_id])
                if stored.file_id not in comp_result.succeeded:
                    # Enqueue in storage_deletions
                    db.add(StorageDeletion(imagekit_file_id=stored.file_id))
                    await db.commit()
            except Exception as comp_exc:
                logger.error(f"Failed compensating storage delete: {comp_exc}")
                db.add(StorageDeletion(imagekit_file_id=stored.file_id))
                await db.commit()
            raise db_exc

    finally:
        # 10. Clean up temp files
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to remove temp dir {temp_dir}: {e}")
