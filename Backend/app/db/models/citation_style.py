from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class CitationStyle(Base):
    __tablename__ = "citation_styles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    style_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sample_string: Mapped[str] = mapped_column(Text, nullable=False)
    formatting_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)

    owner = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "style_name", name="uq_citation_styles_user_name"),
        Index("ix_citation_styles_user_created", "user_id", created_at.desc(), postgresql_where=(is_active.is_(True))),
        Index("ix_citation_styles_name_trgm", "style_name", postgresql_using="gin", postgresql_ops={"style_name": "gin_trgm_ops"}, postgresql_where=(is_active.is_(True))),
    )
