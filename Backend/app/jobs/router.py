from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import check_csrf, get_current_user, get_db, get_storage
from app.db.models.user import User
from app.jobs.events import job_event_generator
from app.jobs.schemas import JobCreate, JobListResponse, JobResponse, ResumeRequest
from app.jobs.service import JobService
from app.storage.base import StorageBackend

router = APIRouter(tags=["jobs"])


@router.post(
    "/files/{file_id}/jobs",
    response_model=JobResponse,
    dependencies=[Depends(check_csrf)],
    operation_id="jobs_create",
)
async def create_job(
    file_id: UUID,
    body: JobCreate,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> JobResponse:
    """
    Starts citation generation for a file.
    Idempotent: returns 202 for a newly created job, 200 if an active job already exists.
    """
    job, created = await JobService.create_job(
        db=db,
        storage=storage,
        owner_id=current_user.id,
        file_id=file_id,
        tex_mode=body.tex_mode,
    )
    response.status_code = status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK
    return JobResponse.model_validate(job)


@router.post(
    "/folders/{folder_id}/jobs",
    response_model=list[JobResponse],
    dependencies=[Depends(check_csrf)],
    operation_id="jobs_create_for_folder",
)
async def create_folder_jobs(
    folder_id: UUID,
    body: JobCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> list[JobResponse]:
    """
    Starts citation generation for all PDF files in a folder.
    Skips files that already have a successful citation unless forced.
    Returns the list of jobs.
    """
    jobs = await JobService.create_folder_jobs(
        db=db,
        storage=storage,
        owner_id=current_user.id,
        folder_id=folder_id,
        tex_mode=body.tex_mode,
    )
    return [JobResponse.model_validate(j) for j in jobs]


@router.get(
    "/jobs/{id}",
    response_model=JobResponse,
    operation_id="jobs_get_detail",
)
async def get_job_detail(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Returns the current status, pending interrupt, or completion reasons of a job."""
    job = await JobService.get_job(db, current_user.id, id)
    return JobResponse.model_validate(job)


@router.get(
    "/jobs",
    response_model=JobListResponse,
    operation_id="jobs_list",
)
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file_id: Optional[UUID] = Query(None, description="Filter jobs by file ID"),
    limit: int = Query(200, ge=1, le=500),
    cursor: Optional[str] = Query(None, description="Opaque pagination cursor"),
) -> JobListResponse:
    """Lists jobs owned by current user (newest first), optionally filtered by file."""
    jobs, next_cursor = await JobService.list_jobs(
        db=db,
        owner_id=current_user.id,
        file_id=file_id,
        limit=limit,
        cursor=cursor,
    )
    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        next_cursor=next_cursor,
    )


@router.post(
    "/jobs/{id}/resume",
    response_model=JobResponse,
    dependencies=[Depends(check_csrf)],
    operation_id="jobs_resume",
)
async def resume_job(
    id: UUID,
    resume_data: ResumeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> JobResponse:
    """Resumes a paused job with title selection/custom title or metadata edits."""
    job = await JobService.resume_job(
        db=db,
        storage=storage,
        owner_id=current_user.id,
        job_id=id,
        resume_data=resume_data,
    )
    return JobResponse.model_validate(job)


@router.post(
    "/jobs/{id}/cancel",
    response_model=JobResponse,
    dependencies=[Depends(check_csrf)],
    operation_id="jobs_cancel",
)
async def cancel_job(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Cancels an active job. Returns 409 if job is already finished."""
    job = await JobService.cancel_job(db, current_user.id, id)
    return JobResponse.model_validate(job)


@router.get(
    "/jobs/{id}/tex",
    operation_id="jobs_download_tex",
)
async def download_job_tex(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Downloads the generated .tex citation document for a succeeded job."""
    tex_content, filename = await JobService.get_job_tex(db, current_user.id, id)
    return Response(
        content=tex_content,
        media_type="text/x-tex",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/jobs/{id}/events",
    operation_id="jobs_events_sse",
)
async def stream_job_events(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Server-Sent Events (SSE) status stream for real-time progress updates."""
    # Ensure job belongs to user
    job = await JobService.get_job(db, current_user.id, id)
    return StreamingResponse(
        job_event_generator(id, job),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
