from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import check_csrf, get_current_user, get_db
from app.db.models.user import User
from app.folders.schemas import FolderCreate, FolderDetailResponse, FolderSummary
from app.folders.service import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get(
    "/root",
    response_model=FolderDetailResponse,
    operation_id="folders_get_root",
)
async def get_root_folder(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=200, ge=1, le=500),
    cursor: Optional[str] = None,
) -> FolderDetailResponse:
    root = await FolderService.get_root_folder(db, current_user.id)
    cur_val = int(cursor) if cursor and cursor.isdigit() else 0
    return await FolderService.get_folder_detail(
        db, current_user.id, root.id, limit=limit, cursor=cur_val
    )


@router.get(
    "/{id}",
    response_model=FolderDetailResponse,
    operation_id="folders_get_detail",
)
async def get_folder_detail(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=200, ge=1, le=500),
    cursor: Optional[str] = None,
) -> FolderDetailResponse:
    cur_val = int(cursor) if cursor and cursor.isdigit() else 0
    return await FolderService.get_folder_detail(
        db, current_user.id, id, limit=limit, cursor=cur_val
    )


@router.post(
    "",
    response_model=FolderSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_csrf)],
    operation_id="folders_create",
)
async def create_folder(
    body: FolderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FolderSummary:
    folder = await FolderService.create_folder(
        db, current_user.id, body.name, body.parent_id
    )
    return FolderSummary.model_validate(folder)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_csrf)],
    operation_id="folders_delete",
)
async def delete_folder(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await FolderService.delete_folder_recursive(db, current_user.id, id)
