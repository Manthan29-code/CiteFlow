from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import check_csrf, get_current_user, get_db
from app.db.models.user import User
from . import service
from .schemas import (
    CitationStyleCreate,
    CitationStyleListResponse,
    CitationStyleResponse,
    CitationStyleUpdate,
    CitationTransformRequest,
    CitationTransformResponse,
)

router = APIRouter(prefix="/styles", tags=["citation-styles"])


@router.post("", response_model=CitationStyleResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_csrf)], operation_id="citation_styles_create")
async def create_style(body: CitationStyleCreate, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    return await service.create_style(db, user.id, body)


@router.get("", response_model=CitationStyleListResponse, operation_id="citation_styles_list")
async def list_styles(db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)], q: str = Query(default="", max_length=120), limit: int = Query(default=20, ge=1, le=100), cursor: str | None = Query(default=None)):
    return await service.list_styles(db, user.id, q, limit, cursor)


@router.get("/{style_id}", response_model=CitationStyleResponse, operation_id="citation_styles_get")
async def get_style(style_id: UUID, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    return await service.get_style(db, user.id, style_id)


@router.put("/{style_id}", response_model=CitationStyleResponse, dependencies=[Depends(check_csrf)], operation_id="citation_styles_update")
async def update_style(style_id: UUID, body: CitationStyleUpdate, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    return await service.update_style(db, user.id, style_id, body)


@router.delete("/{style_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_csrf)], operation_id="citation_styles_delete")
async def delete_style(style_id: UUID, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    await service.delete_style(db, user.id, style_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{style_id}/transform", response_model=CitationTransformResponse, dependencies=[Depends(check_csrf)], operation_id="citation_styles_transform")
async def transform_style(style_id: UUID, body: CitationTransformRequest, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    return await service.transform_citation(db, user.id, style_id, body.source_citation)
