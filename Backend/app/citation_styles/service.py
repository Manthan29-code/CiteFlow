import re
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utc_now
from app.db.models.citation_style import CitationStyle
from app.citation_styles.schemas import CitationStyleCreate, CitationStyleUpdate
from citegen.latex.style_engine import (
    ALLOWED_TEMPLATE_FIELDS,
    format_bibitem_with_style,
    get_sample_metadata,
    validate_citation_template,
)


def slugify(text: str) -> str:
    """Generates a clean URL/storage slug from a string."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return cleaned.strip("-") or "style"


class CitationStyleService:
    @classmethod
    async def list_styles(cls, db: AsyncSession, owner_id: UUID) -> List[CitationStyle]:
        """
        Lists all styles accessible to the user:
        built-in system styles and custom styles owned by owner_id.
        """
        stmt = (
            select(CitationStyle)
            .where(
                or_(
                    CitationStyle.is_builtin.is_(True),
                    CitationStyle.owner_id == owner_id,
                )
            )
            .order_by(CitationStyle.is_builtin.desc(), CitationStyle.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_style(cls, db: AsyncSession, owner_id: UUID, style_id: UUID) -> CitationStyle:
        """Fetches a citation style by ID ensuring user has access."""
        stmt = select(CitationStyle).where(
            CitationStyle.id == style_id,
            or_(
                CitationStyle.is_builtin.is_(True),
                CitationStyle.owner_id == owner_id,
            ),
        )
        style = (await db.execute(stmt)).scalar_one_or_none()
        if not style:
            raise AppError(
                status_code=404,
                code="style_not_found",
                message=f"Citation style '{style_id}' not found.",
            )
        return style

    @classmethod
    async def create_style(
        cls,
        db: AsyncSession,
        owner_id: UUID,
        data: CitationStyleCreate,
    ) -> CitationStyle:
        """Validates and creates a new custom citation style for the user."""
        # 1. Validate template syntax
        is_valid, errors = validate_citation_template(data.template)
        if not is_valid:
            raise AppError(
                status_code=422,
                code="invalid_template",
                message=f"Invalid citation template: {'; '.join(errors)}",
            )

        name = data.name.strip()
        slug = slugify(name)

        # 2. Check name collision for this user
        existing_stmt = select(CitationStyle).where(
            CitationStyle.owner_id == owner_id,
            CitationStyle.name.ilike(name),
        )
        if (await db.execute(existing_stmt)).scalar_one_or_none():
            raise AppError(
                status_code=409,
                code="style_name_exists",
                message=f"A citation style named '{name}' already exists in your library.",
            )

        style = CitationStyle(
            owner_id=owner_id,
            name=name,
            slug=slug,
            template=data.template.strip(),
            is_builtin=False,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(style)
        await db.commit()
        await db.refresh(style)
        return style

    @classmethod
    async def update_style(
        cls,
        db: AsyncSession,
        owner_id: UUID,
        style_id: UUID,
        data: CitationStyleUpdate,
    ) -> CitationStyle:
        """Updates an existing custom citation style. Built-in styles cannot be edited."""
        stmt = select(CitationStyle).where(CitationStyle.id == style_id)
        style = (await db.execute(stmt)).scalar_one_or_none()

        if not style:
            raise AppError(
                status_code=404,
                code="style_not_found",
                message=f"Citation style '{style_id}' not found.",
            )

        if style.is_builtin:
            raise AppError(
                status_code=403,
                code="cannot_modify_builtin_style",
                message="Built-in system citation styles cannot be edited.",
            )

        if style.owner_id != owner_id:
            raise AppError(
                status_code=404,
                code="style_not_found",
                message=f"Citation style '{style_id}' not found.",
            )

        # Validate template if provided
        if data.template is not None:
            is_valid, errors = validate_citation_template(data.template)
            if not is_valid:
                raise AppError(
                    status_code=422,
                    code="invalid_template",
                    message=f"Invalid citation template: {'; '.join(errors)}",
                )
            style.template = data.template.strip()

        # Update name if provided
        if data.name is not None and data.name.strip():
            new_name = data.name.strip()
            # Check unique name
            existing_stmt = select(CitationStyle).where(
                CitationStyle.owner_id == owner_id,
                CitationStyle.name.ilike(new_name),
                CitationStyle.id != style_id,
            )
            if (await db.execute(existing_stmt)).scalar_one_or_none():
                raise AppError(
                    status_code=409,
                    code="style_name_exists",
                    message=f"A citation style named '{new_name}' already exists in your library.",
                )
            style.name = new_name
            style.slug = slugify(new_name)

        style.updated_at = utc_now()
        await db.commit()
        await db.refresh(style)
        return style

    @classmethod
    async def delete_style(cls, db: AsyncSession, owner_id: UUID, style_id: UUID) -> None:
        """Deletes a custom citation style. Built-in styles cannot be deleted."""
        stmt = select(CitationStyle).where(CitationStyle.id == style_id)
        style = (await db.execute(stmt)).scalar_one_or_none()

        if not style:
            raise AppError(
                status_code=404,
                code="style_not_found",
                message=f"Citation style '{style_id}' not found.",
            )

        if style.is_builtin:
            raise AppError(
                status_code=403,
                code="cannot_delete_builtin_style",
                message="Built-in system citation styles cannot be deleted.",
            )

        if style.owner_id != owner_id:
            raise AppError(
                status_code=404,
                code="style_not_found",
                message=f"Citation style '{style_id}' not found.",
            )

        await db.delete(style)
        await db.commit()

    @classmethod
    def validate_and_preview(cls, template: str) -> Tuple[bool, List[str], Optional[str]]:
        """
        Validates template syntax and produces a live LaTeX \\bibitem preview
        using standard sample metadata (Ghosh 2017).
        """
        is_valid, errors = validate_citation_template(template)
        preview: Optional[str] = None
        if is_valid:
            try:
                sample_meta = get_sample_metadata()
                preview = format_bibitem_with_style(
                    metadata=sample_meta,
                    template=template,
                    citation_key="Ghosh2017",
                )
            except Exception as e:
                errors.append(f"Preview rendering error: {str(e)}")
                is_valid = False

        return is_valid, errors, preview

