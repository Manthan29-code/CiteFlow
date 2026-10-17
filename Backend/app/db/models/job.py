from datetime import datetime
from uuid import UUID, uuid4
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_id: Mapped[UUID] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    tex_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="standalone")
    pending_interrupt: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    result_tex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    reasons: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), onupdate=utc_now, nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship("User")
    file = relationship("File")

    __table_args__ = (
        Index("ix_jobs_owner_created", "owner_id", created_at.desc()),
        Index("ix_jobs_file_id", "file_id"),
        Index(
            "uq_jobs_file_active",
            "file_id",
            unique=True,
            postgresql_where=(
                status.in_(["queued", "running", "needs_title_confirmation", "needs_review"])
            ),
        ),
    )
