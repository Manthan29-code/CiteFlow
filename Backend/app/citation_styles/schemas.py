from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CitationStyleCreate(BaseModel):
    style_name: str = Field(min_length=1, max_length=120)
    sample_string: str = Field(min_length=10, max_length=12000)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("style_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Style name cannot be empty.")
        return value


class CitationStyleUpdate(BaseModel):
    style_name: str | None = Field(default=None, min_length=1, max_length=120)
    sample_string: str | None = Field(default=None, min_length=10, max_length=12000)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("style_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Style name cannot be empty.")
        return value


class CitationStyleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    style_name: str
    description: str | None
    sample_string: str
    formatting_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CitationStyleListResponse(BaseModel):
    items: list[CitationStyleResponse]
    next_cursor: str | None = None


class CitationTransformRequest(BaseModel):
    source_citation: str = Field(min_length=10, max_length=12000)


class CitationTransformResponse(BaseModel):
    reformatted_citation: str
    diff_summary: dict[str, Any] | None = None
