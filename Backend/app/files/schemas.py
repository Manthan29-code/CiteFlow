from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class FileResponse(BaseModel):
    id: UUID
    name: str
    ext: str
    size_bytes: int
    folder_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SignedUrlResponse(BaseModel):
    url: str
    expires_in: int
