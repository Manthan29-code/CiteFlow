from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: UUID


class Breadcrumb(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class FolderSummary(BaseModel):
    id: UUID
    name: str
    parent_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


class FileSummary(BaseModel):
    id: UUID
    name: str
    ext: str
    size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True


class FolderDetailResponse(BaseModel):
    folder: FolderSummary
    breadcrumbs: List[Breadcrumb]
    folders: List[FolderSummary]
    files: List[FileSummary]
    next_cursor: Optional[str] = None
