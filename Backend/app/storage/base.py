from dataclasses import dataclass, field
from typing import BinaryIO, Dict, List, Optional, Protocol
from uuid import UUID


@dataclass
class StoredFile:
    file_id: str
    file_path: str
    url: Optional[str] = None


@dataclass
class DeleteResult:
    succeeded: List[str] = field(default_factory=list)
    failed: Dict[str, str] = field(default_factory=dict)


class StorageBackend(Protocol):
    async def upload(self, file: BinaryIO, *, owner_id: UUID, stored_name: str) -> StoredFile:
        """Uploads a file to storage as private and returns the StoredFile metadata."""
        ...

    async def signed_url(self, stored_path: str, *, expires_in: int) -> str:
        """Generates a short-lived signed URL for downloading/viewing the private file."""
        ...

    async def delete_many(self, file_ids: List[str]) -> DeleteResult:
        """Deletes files from storage by their storage IDs. Reports per-id success/failure."""
        ...
