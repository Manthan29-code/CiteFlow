import io
from typing import BinaryIO, Dict, List
from uuid import UUID, uuid4

from app.storage.base import DeleteResult, StorageBackend, StoredFile


class FakeStorage(StorageBackend):
    """
    In-memory StorageBackend implementation for tests and local development.
    Can be configured to simulate failures.
    """

    def __init__(self, should_fail_upload: bool = False, should_fail_delete: bool = False):
        self.should_fail_upload = should_fail_upload
        self.should_fail_delete = should_fail_delete
        self.files: Dict[str, bytes] = {}  # file_id -> content
        self.file_paths: Dict[str, str] = {}  # file_id -> stored_path
        self.path_to_id: Dict[str, str] = {}  # stored_path -> file_id

    async def upload(self, file: BinaryIO, *, owner_id: UUID, stored_name: str) -> StoredFile:
        if self.should_fail_upload:
            raise RuntimeError("FakeStorage simulated upload error")

        file_id = f"fake_{uuid4().hex[:12]}"
        stored_path = f"/citegen/{owner_id}/{stored_name}"

        content = file.read()
        self.files[file_id] = content
        self.file_paths[file_id] = stored_path
        self.path_to_id[stored_path] = file_id

        return StoredFile(
            file_id=file_id,
            file_path=stored_path,
            url=f"https://fake-ik.test{stored_path}",
        )

    async def signed_url(self, stored_path: str, *, expires_in: int) -> str:
        return f"https://fake-ik.test{stored_path}?token=fake_signed_token&expires={expires_in}"

    async def delete_many(self, file_ids: List[str]) -> DeleteResult:
        result = DeleteResult()
        for fid in file_ids:
            if self.should_fail_delete:
                result.failed[fid] = "FakeStorage simulated delete error"
                continue

            if fid in self.files:
                del self.files[fid]
                path = self.file_paths.pop(fid, None)
                if path and path in self.path_to_id:
                    del self.path_to_id[path]
            # Rule 4.2.5: Not found is treated as success
            result.succeeded.append(fid)

        return result
