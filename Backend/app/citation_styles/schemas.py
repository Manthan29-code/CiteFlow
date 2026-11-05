from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CitationStyleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Display name of the citation style")
    template: str = Field(min_length=5, max_length=2000, description="LaTeX \\bibitem template with <TAG> fields")


class CitationStyleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    template: Optional[str] = Field(default=None, min_length=5, max_length=2000)


class CitationStyleResponse(BaseModel):
    id: UUID
    owner_id: Optional[UUID] = None
    name: str
    slug: str
    template: str
    is_builtin: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ValidateTemplateRequest(BaseModel):
    template: str = Field(description="LaTeX \\bibitem template to validate")


class ValidateTemplateResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    preview: Optional[str] = None


class AllowedFieldsResponse(BaseModel):
    fields: List[str]

