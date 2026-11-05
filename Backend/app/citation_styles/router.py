from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import check_csrf, get_current_user, get_db
from app.db.models.user import User
from app.citation_styles.schemas import (
    AllowedFieldsResponse,
    CitationStyleCreate,
    CitationStyleResponse,
    CitationStyleUpdate,
    ValidateTemplateRequest,
    ValidateTemplateResponse,
)
from app.citation_styles.service import CitationStyleService
from citegen.latex.style_engine import ALLOWED_TEMPLATE_FIELDS

router = APIRouter(prefix="/citation-styles", tags=["citation-styles"])


@router.get(
    "",
    response_model=List[CitationStyleResponse],
    operation_id="citation_styles_list",
)
async def list_citation_styles(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[CitationStyleResponse]:
    """Lists all built-in styles and custom styles owned by the user."""
    styles = await CitationStyleService.list_styles(db, current_user.id)
    return [CitationStyleResponse.model_validate(s) for s in styles]


@router.get(
    "/fields",
    response_model=AllowedFieldsResponse,
    operation_id="citation_styles_get_fields",
)
async def get_allowed_fields(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AllowedFieldsResponse:
    """Returns the list of allowed <TAG> metadata fields for template autocomplete."""
    return AllowedFieldsResponse(fields=sorted(list(ALLOWED_TEMPLATE_FIELDS)))


@router.post(
    "/validate",
    response_model=ValidateTemplateResponse,
    operation_id="citation_styles_validate_template",
)
async def validate_template(
    body: ValidateTemplateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ValidateTemplateResponse:
    """Validates a citation template and returns a live LaTeX preview using sample metadata."""
    is_valid, errors, preview = CitationStyleService.validate_and_preview(body.template)
    return ValidateTemplateResponse(valid=is_valid, errors=errors, preview=preview)


@router.get(
    "/{id}",
    response_model=CitationStyleResponse,
    operation_id="citation_styles_get_detail",
)
async def get_citation_style(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CitationStyleResponse:
    """Fetches a specific citation style by ID."""
    style = await CitationStyleService.get_style(db, current_user.id, id)
    return CitationStyleResponse.model_validate(style)


@router.post(
    "",
    response_model=CitationStyleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_csrf)],
    operation_id="citation_styles_create",
)
async def create_citation_style(
    body: CitationStyleCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CitationStyleResponse:
    """Creates a new custom citation style."""
    style = await CitationStyleService.create_style(db, current_user.id, body)
    return CitationStyleResponse.model_validate(style)


@router.put(
    "/{id}",
    response_model=CitationStyleResponse,
    dependencies=[Depends(check_csrf)],
    operation_id="citation_styles_update",
)
async def update_citation_style(
    id: UUID,
    body: CitationStyleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CitationStyleResponse:
    """Updates an existing custom citation style. Built-in styles cannot be edited."""
    style = await CitationStyleService.update_style(db, current_user.id, id, body)
    return CitationStyleResponse.model_validate(style)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_csrf)],
    operation_id="citation_styles_delete",
)
async def delete_citation_style(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Deletes a custom citation style. Built-in styles cannot be deleted."""
    await CitationStyleService.delete_style(db, current_user.id, id)
    return None

