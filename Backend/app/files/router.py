from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import check_csrf, get_current_user, get_db, get_storage
from app.db.models.user import User
from app.files.schemas import FileResponse, SignedUrlResponse
from app.files.service import FileService
from app.files.upload import handle_file_upload
from app.storage.base import StorageBackend

router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_csrf)],
    operation_id="files_upload",
)
async def upload_file(
    file: UploadFile,
    folder_id: Annotated[UUID, Form()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> FileResponse:
    db_file = await handle_file_upload(
        db=db,
        storage=storage,
        owner_id=current_user.id,
        folder_id=folder_id,
        upload=file,
    )
    return FileResponse.model_validate(db_file)


@router.get(
    "/{id}",
    response_model=FileResponse,
    operation_id="files_get_detail",
)
async def get_file_detail(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    file = await FileService.get_file(db, current_user.id, id)
    return FileResponse.model_validate(file)


@router.get(
    "/{id}/url",
    response_model=SignedUrlResponse,
    operation_id="files_get_signed_url",
)
async def get_signed_url(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> SignedUrlResponse:
    return await FileService.get_signed_url(db, storage, current_user.id, id)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_csrf)],
    operation_id="files_delete",
)
async def delete_file(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await FileService.delete_file(db, current_user.id, id)
