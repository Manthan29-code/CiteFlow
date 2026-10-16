import asyncio
import logging
from typing import BinaryIO, List
from uuid import UUID

from app.core.config import settings
from app.storage.base import DeleteResult, StorageBackend, StoredFile

logger = logging.getLogger(__name__)


class ImageKitStorage(StorageBackend):
    def __init__(self, private_key: str | None = None, url_endpoint: str | None = None, base_folder: str | None = None):
        self.private_key = private_key or settings.IMAGEKIT_PRIVATE_KEY
        self.url_endpoint = url_endpoint or settings.IMAGEKIT_URL_ENDPOINT
        self.base_folder = base_folder or settings.IMAGEKIT_BASE_FOLDER
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from imagekitio import ImageKit
                self._client = ImageKit(private_key=self.private_key)
            except Exception as e:
                logger.error(f"Failed to initialize ImageKit client: {e}")
                raise
        return self._client

    async def upload(self, file: BinaryIO, *, owner_id: UUID, stored_name: str) -> StoredFile:
        client = self._get_client()
        folder_path = f"{self.base_folder.rstrip('/')}/{owner_id}"

        def _do_upload():
            return client.files.upload(
                file=file,
                file_name=stored_name,
                folder=folder_path,
                is_private_file=True,
                use_unique_file_name=True,
            )

        resp = await asyncio.to_thread(_do_upload)
        # Verify file_id and path from response
        file_id = getattr(resp, "file_id", None) or getattr(resp, "fileId", "")
        file_path = getattr(resp, "file_path", None) or getattr(resp, "filePath", "")
        if not file_path:
            # Fallback to folder_path / name if not directly on response
            file_path = getattr(resp, "name", stored_name)
            if not file_path.startswith("/"):
                file_path = f"{folder_path}/{file_path}"
        url = getattr(resp, "url", None)

        return StoredFile(file_id=str(file_id), file_path=str(file_path), url=url)

    async def signed_url(self, stored_path: str, *, expires_in: int) -> str:
        client = self._get_client()

        def _build():
            return client.helper.build_url(
                url_endpoint=self.url_endpoint,
                src=stored_path,
                signed=True,
                expires_in=expires_in,
            )

        return await asyncio.to_thread(_build)

    async def delete_many(self, file_ids: List[str]) -> DeleteResult:
        if not file_ids:
            return DeleteResult()

        client = self._get_client()
        result = DeleteResult()

        def _delete_sync():
            # Try bulk delete first if supported by SDK, else loop individual delete
            try:
                if hasattr(client.files, "bulk") and hasattr(client.files.bulk, "delete"):
                    # ImageKit bulk delete accepts file_ids list
                    bulk_res = client.files.bulk.delete(file_ids=file_ids)
                    # Bulk delete response typically contains successfullyDeletedFileIds
                    succ = getattr(bulk_res, "successfully_deleted_file_ids", None) or getattr(
                        bulk_res, "successfullyDeletedFileIds", None
                    )
                    if succ is not None:
                        result.succeeded.extend(succ)
                        # Add any missing as failed or check failed list
                        missing = set(file_ids) - set(succ)
                        for m in missing:
                            result.failed[m] = "Bulk delete did not confirm deletion"
                        return

            except Exception as bulk_exc:
                logger.warning(f"Bulk delete failed, falling back to sequential delete: {bulk_exc}")

            # Sequential fallback
            for fid in file_ids:
                try:
                    client.files.delete(file_id=fid)
                    result.succeeded.append(fid)
                except Exception as ex:
                    msg = str(ex).lower()
                    # Rule 4.2.5: Treat "file not found / already deleted" as success
                    if "not found" in msg or "404" in msg or "already deleted" in msg:
                        result.succeeded.append(fid)
                    else:
                        result.failed[fid] = str(ex)

        await asyncio.to_thread(_delete_sync)
        return result
