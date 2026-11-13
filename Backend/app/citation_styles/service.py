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

# Canonical clean lowercase presets for system built-in styles
BUILTIN_PRESET_TEMPLATES = {
    "iop-default": r"\bibitem{citation key} authors year \textit{journal abbreviation} \href{doi url}{\textbf{volume} locator}.",
    "ama-vancouver": r"\bibitem{citation key} authors last first . title. journal abbreviation year;volume(issue):article number. doi:doi.",
    "ieee": r"\bibitem{citation key} authors first. last, ``title,'' \textit{journal}, vol. volume, no. issue, Article article number, year. \href{doi url}{doi url}",
}


def slugify(text: str) -> str:
    """Generates a clean URL/storage slug from a string."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return cleaned.strip("-") or "style"


class CitationStyleService:
    @classmethod
    async def list_styles(cls, db: AsyncSession, owner_id: UUID) -> List[CitationStyle]:
        """
        Lists all styles accessible to the user:
        - built-in system styles (excluding any that the user has deleted or overridden)
        - custom styles owned by owner_id (excluding tombstones)
        """
        # 1. Fetch user-owned styles
        user_stmt = select(CitationStyle).where(CitationStyle.owner_id == owner_id)
        user_records = list((await db.execute(user_stmt)).scalars().all())

        deleted_slugs = {
            s.slug.replace("deleted:", "")
            for s in user_records
            if s.slug.startswith("deleted:")
        }
        active_user_styles = [
            s for s in user_records
            if not s.slug.startswith("deleted:")
        ]
        user_slugs = {s.slug for s in active_user_styles}

        # 2. Fetch system built-in styles
        builtin_stmt = (
            select(CitationStyle)
            .where(CitationStyle.is_builtin.is_(True))
            .order_by(CitationStyle.created_at.asc())
        )
        builtin_records = list((await db.execute(builtin_stmt)).scalars().all())

        # Auto-sync built-in presets only for the core IOP default style
        needs_commit = False
        for s in builtin_records:
            if s.slug == "iop-default":
                canonical = BUILTIN_PRESET_TEMPLATES["iop-default"]
                if s.template != canonical:
                    s.template = canonical
                    s.updated_at = utc_now()
                    db.add(s)
                    needs_commit = True
                if s.name != "IOP":
                    s.name = "IOP"
                    s.updated_at = utc_now()
                    db.add(s)
                    needs_commit = True

        if needs_commit:
            try:
                await db.commit()
            except Exception:
                await db.rollback()

        # 3. Filter built-in styles: exclude deleted or overridden ones
        visible_builtins = [
            s for s in builtin_records
            if s.slug not in deleted_slugs and s.slug not in user_slugs
        ]

        # Put IOP first, then remaining built-ins, then custom styles
        iop_styles = [s for s in visible_builtins if s.slug == "iop-default"]
        other_builtins = [s for s in visible_builtins if s.slug != "iop-default"]

        return iop_styles + other_builtins + active_user_styles

    @classmethod
    async def get_style(cls, db: AsyncSession, owner_id: UUID, style_id: UUID) -> CitationStyle:
        """Fetches a citation style by ID ensuring user has access and hasn't deleted it."""
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

        if style.slug.startswith("deleted:"):
            raise AppError(
                status_code=404,
                code="style_not_found",
                message=f"Citation style '{style_id}' not found.",
            )

        # Check if user deleted this built-in style
        if style.is_builtin:
            tombstone_stmt = select(CitationStyle).where(
                CitationStyle.owner_id == owner_id,
                CitationStyle.slug == f"deleted:{style.slug}",
            )
            if (await db.execute(tombstone_stmt)).scalar_one_or_none():
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
        """
        Updates a citation style for this user.
        - Default IOP cannot be modified.
        - Built-in styles (IEEE, AMA) are forked into user-owned styles so other users are unaffected.
        - Custom styles are modified directly.
        """
        stmt = select(CitationStyle).where(CitationStyle.id == style_id)
        style = (await db.execute(stmt)).scalar_one_or_none()

        if not style:
            raise AppError(
                status_code=404,
                code="style_not_found",
                message=f"Citation style '{style_id}' not found.",
            )

        if style.slug == "iop-default" or style.name.strip().lower() == "iop":
            raise AppError(
                status_code=403,
                code="cannot_modify_default_style",
                message="The default IOP citation style cannot be modified.",
            )

        if style.owner_id is not None and style.owner_id != owner_id:
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

        new_name = data.name.strip() if data.name is not None and data.name.strip() else style.name
        new_template = data.template.strip() if data.template is not None else style.template

        # Check unique name for this user
        existing_stmt = select(CitationStyle).where(
            CitationStyle.owner_id == owner_id,
            CitationStyle.name.ilike(new_name),
            CitationStyle.id != style_id,
            ~CitationStyle.slug.startswith("deleted:"),
        )
        if (await db.execute(existing_stmt)).scalar_one_or_none():
            raise AppError(
                status_code=409,
                code="style_name_exists",
                message=f"A citation style named '{new_name}' already exists in your library.",
            )

        # Case 1: Editing a shared built-in style -> Fork as a user-owned style (Copy-On-Write)
        if style.owner_id is None:
            forked_style = CitationStyle(
                owner_id=owner_id,
                name=new_name,
                slug=style.slug,
                template=new_template,
                is_builtin=False,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(forked_style)
            await db.flush()

            # Update this user's jobs referencing the old built-in style
            from app.db.models.job import Job
            from sqlalchemy import update
            await db.execute(
                update(Job)
                .where(Job.owner_id == owner_id, Job.style_id == style.id)
                .values(style_id=forked_style.id)
            )

            await db.commit()
            await db.refresh(forked_style)
            return forked_style

        # Case 2: Editing user's own style
        style.name = new_name
        style.template = new_template
        style.updated_at = utc_now()
        await db.commit()
        await db.refresh(style)
        return style

    @classmethod
    async def delete_style(cls, db: AsyncSession, owner_id: UUID, style_id: UUID) -> None:
        """
        Deletes a citation style for this user.
        - Default IOP cannot be deleted.
        - For built-in styles (IEEE, AMA), marks a tombstone for this user so other users are unaffected.
        - For custom styles, deletes the user's record.
        """
        stmt = select(CitationStyle).where(CitationStyle.id == style_id)
        style = (await db.execute(stmt)).scalar_one_or_none()

        if not style:
            raise AppError(
                status_code=404,
                code="style_not_found",
                message=f"Citation style '{style_id}' not found.",
            )

        if style.slug == "iop-default" or style.name.strip().lower() == "iop":
            raise AppError(
                status_code=403,
                code="cannot_delete_default_style",
                message="The default IOP citation style cannot be deleted.",
            )

        if style.owner_id is not None and style.owner_id != owner_id:
            raise AppError(
                status_code=404,
                code="style_not_found",
                message=f"Citation style '{style_id}' not found.",
            )

        from app.db.models.job import Job
        from sqlalchemy import update

        # Unlink only this user's jobs referencing this style
        await db.execute(
            update(Job)
            .where(Job.owner_id == owner_id, Job.style_id == style_id)
            .values(style_id=None)
        )

        # Case 1: Built-in style -> Do NOT delete shared row! Record tombstone for this user only.
        if style.owner_id is None:
            tombstone = CitationStyle(
                owner_id=owner_id,
                name=style.name,
                slug=f"deleted:{style.slug}",
                template="deleted",
                is_builtin=False,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(tombstone)
            await db.commit()
            return

        # Case 2: User-owned style that had overridden a built-in -> Delete user copy AND record tombstone
        if style.slug in BUILTIN_PRESET_TEMPLATES:
            tombstone = CitationStyle(
                owner_id=owner_id,
                name=style.name,
                slug=f"deleted:{style.slug}",
                template="deleted",
                is_builtin=False,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(tombstone)

        # Delete the user's custom row
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
