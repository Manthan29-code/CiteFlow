from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class JobCreate(BaseModel):
    tex_mode: Literal["standalone", "fragment"] = "standalone"


class JobResponse(BaseModel):
    id: UUID
    owner_id: UUID
    file_id: UUID
    status: str
    tex_mode: str
    pending_interrupt: Optional[Dict[str, Any]] = None
    result_metadata: Optional[Dict[str, Any]] = None
    reasons: Optional[List[Any]] = None
    error_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    items: List[JobResponse]
    next_cursor: Optional[str] = None


ALLOWED_METADATA_FIELDS = {
    "title",
    "authors",
    "year",
    "journal",
    "journal_abbreviation",
    "doi_url",
    "volume",
    "issue",
    "first_page",
    "article_number",
}


class ResumeRequest(BaseModel):
    action: str  # "select" | "custom" | "accept" | "edit" | "skip"
    index: Optional[int] = None
    title: Optional[str] = None
    edits: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "ResumeRequest":
        act = self.action.lower().strip()
        self.action = act

        if act == "select":
            if self.index is None or self.index < 0:
                raise ValueError("action='select' requires a non-negative integer 'index'.")

        elif act == "custom":
            if not self.title or not self.title.strip():
                raise ValueError("action='custom' requires a non-empty 'title'.")
            self.title = self.title.strip()
            if len(self.title) > 300:
                raise ValueError("Custom title is too long (max 300 characters).")
            # Disallow control characters
            if any(ord(c) < 32 and c not in "\t\n\r" for c in self.title):
                raise ValueError("Custom title contains invalid control characters.")

        elif act == "edit":
            if not self.edits or not isinstance(self.edits, dict):
                raise ValueError("action='edit' requires an 'edits' dictionary.")
            unknown = set(self.edits.keys()) - ALLOWED_METADATA_FIELDS
            if unknown:
                raise ValueError(
                    f"Unknown edit fields: {sorted(unknown)}. Allowed: {sorted(ALLOWED_METADATA_FIELDS)}"
                )
            # Type-check allowed fields
            for key, val in self.edits.items():
                if val is None:
                    continue
                if key in ("title", "journal", "journal_abbreviation", "doi_url"):
                    if not isinstance(val, str):
                        raise ValueError(f"Field '{key}' must be a string.")
                elif key == "year":
                    if not isinstance(val, (int, str)):
                        raise ValueError(f"Field 'year' must be an integer or integer string.")
                    try:
                        int(val)
                    except ValueError:
                        raise ValueError(f"Field 'year' must represent a valid integer.")
                elif key == "authors":
                    if not isinstance(val, list):
                        raise ValueError("Field 'authors' must be a list.")
                elif key in ("volume", "issue", "first_page", "article_number"):
                    if not isinstance(val, (str, int)):
                        raise ValueError(f"Field '{key}' must be a string or number.")

        elif act in ("accept", "skip"):
            pass

        else:
            raise ValueError(
                f"Unknown action: '{self.action}'. Must be select, custom, accept, edit, or skip."
            )

        return self

