import asyncio
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import utc_now
from app.db.models.file import File
from app.db.models.job import Job
from app.db.session import async_session_maker
from app.files.handlers.base import get_handler
from app.jobs.checkpointer import get_checkpointer
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

_job_semaphore: Optional[asyncio.Semaphore] = None
_running_tasks: Dict[UUID, asyncio.Task] = {}
_status_listeners: Dict[UUID, list[asyncio.Queue]] = {}
_crossref_sem: Optional[asyncio.Semaphore] = None
_openalex_sem: Optional[asyncio.Semaphore] = None


def init_provider_semaphores() -> None:
    global _crossref_sem, _openalex_sem
    try:
        from citegen.providers.crossref import set_crossref_semaphore
        from citegen.providers.openalex import set_openalex_semaphore

        if _crossref_sem is None:
            _crossref_sem = asyncio.Semaphore(settings.CROSSREF_MAX_CONCURRENCY)
            set_crossref_semaphore(_crossref_sem)
        if _openalex_sem is None:
            _openalex_sem = asyncio.Semaphore(settings.OPENALEX_MAX_CONCURRENCY)
            set_openalex_semaphore(_openalex_sem)
    except Exception as e:
        logger.warning(f"Could not initialize provider semaphores: {e}")


def get_job_semaphore() -> asyncio.Semaphore:
    global _job_semaphore
    if _job_semaphore is None:
        _job_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)
    init_provider_semaphores()
    return _job_semaphore



def register_listener(job_id: UUID) -> asyncio.Queue:
    """Registers an SSE listener queue for status events on a job."""
    q: asyncio.Queue = asyncio.Queue()
    if job_id not in _status_listeners:
        _status_listeners[job_id] = []
    _status_listeners[job_id].append(q)
    return q


def unregister_listener(job_id: UUID, q: asyncio.Queue) -> None:
    """Removes an SSE listener queue."""
    if job_id in _status_listeners and q in _status_listeners[job_id]:
        _status_listeners[job_id].remove(q)
        if not _status_listeners[job_id]:
            del _status_listeners[job_id]


def broadcast_status(job_id: UUID, event_data: dict) -> None:
    """Broadcasts a status update to all connected SSE clients."""
    if job_id in _status_listeners:
        for q in _status_listeners[job_id]:
            q.put_nowait(event_data)


def cancel_running_task(job_id: UUID) -> bool:
    """Cancels in-memory running task if currently active."""
    task = _running_tasks.get(job_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


async def execute_job(
    job_id: UUID,
    storage: StorageBackend,
    resume_payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Executes a citation generation job using the core LangGraph pipeline:
    1. Acquires slot under MAX_CONCURRENT_JOBS semaphore.
    2. Streams file to secure temp directory.
    3. Runs graph with persistent checkpointer.
    4. Handles interrupt (pauses and ends task) or completion (saves .tex/metadata).
    5. Cleans up temp directory in finally.
    """
    sem = get_job_semaphore()
    temp_dir: Optional[Path] = None

    async with sem:
        async with async_session_maker() as db:
            # 1. Fetch job and update status to running
            stmt = select(Job).where(Job.id == job_id)
            job = (await db.execute(stmt)).scalar_one_or_none()
            if not job or job.status in ("canceled", "failed", "succeeded"):
                return

            job.status = "running"
            job.updated_at = utc_now()
            await db.commit()
            broadcast_status(job_id, {"status": "running"})

            file_id = job.file_id
            tex_mode = job.tex_mode

            # Fetch file record
            f_stmt = select(File).where(File.id == file_id)
            file_rec = (await db.execute(f_stmt)).scalar_one_or_none()
            if not file_rec:
                job.status = "failed"
                job.error_code = "file_not_found"
                job.finished_at = utc_now()
                await db.commit()
                broadcast_status(job_id, {"status": "failed", "error_code": "file_not_found"})
                return

            imagekit_path = file_rec.imagekit_path
            ext = file_rec.ext

        # 2. Setup temp directory
        temp_parent = Path(settings.TEMP_DIR)
        temp_dir = temp_parent / str(job_id)
        temp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        local_doc_path = temp_dir / f"input.{ext}"

        try:
            # 3. Stream file from storage
            signed_url = await storage.signed_url(imagekit_path, expires_in=settings.SIGNED_URL_EXPIRES_SECONDS)
            max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("GET", signed_url) as resp:
                    resp.raise_for_status()
                    downloaded = 0
                    with open(local_doc_path, "wb") as f_out:
                        async for chunk in resp.aiter_bytes():
                            downloaded += len(chunk)
                            if downloaded > max_bytes:
                                raise ValueError(f"File size exceeded {settings.MAX_UPLOAD_MB}MB limit during download.")
                            f_out.write(chunk)

            # Re-validate via handler
            handler = get_handler(ext)
            if handler:
                await handler.validate(local_doc_path)

            # 4. Run LangGraph via citegen.api.run_file
            from citegen.api import render_single_record, run_file
            from langgraph.checkpoint.base import BaseCheckpointSaver
            try:
                checkpointer = get_checkpointer()
                if not isinstance(checkpointer, BaseCheckpointSaver):
                    logger.warning(f"Checkpointer {type(checkpointer)} is not a BaseCheckpointSaver. Falling back to MemorySaver.")
                    from langgraph.checkpoint.memory import MemorySaver
                    checkpointer = MemorySaver()
            except Exception as cp_err:
                logger.warning(f"Could not get configured checkpointer: {cp_err}. Using MemorySaver.")
                from langgraph.checkpoint.memory import MemorySaver
                checkpointer = MemorySaver()

            # Execute with overall timeout
            run_coro = run_file(
                file_path=local_doc_path,
                thread_id=str(job_id),
                checkpointer=checkpointer,
                resume_payload=resume_payload,
                interactive=True,
                temp_dir=temp_dir,
            )
            result = await asyncio.wait_for(run_coro, timeout=float(settings.JOB_TIMEOUT_SECONDS))

            # 5. Process results
            async with async_session_maker() as db:
                stmt = select(Job).where(Job.id == job_id)
                job = (await db.execute(stmt)).scalar_one()

                if result.status == "interrupted":
                    kind = (result.pending_interrupt or {}).get("kind", "user_review")
                    new_status = "needs_title_confirmation" if kind == "confirm_title" else "needs_review"
                    job.status = new_status
                    job.pending_interrupt = result.pending_interrupt
                    job.result_metadata = result.draft_record
                    job.updated_at = utc_now()
                    await db.commit()
                    broadcast_status(job_id, {"status": new_status, "pending_interrupt": job.pending_interrupt})

                elif result.status == "accepted":
                    rendered_tex = render_single_record(
                        metadata=result.draft_record,
                        raw_bibitem=result.raw_bibitem,
                        standalone=(tex_mode == "standalone"),
                    )
                    job.status = "succeeded"
                    job.result_tex = rendered_tex
                    job.result_metadata = result.draft_record
                    job.finished_at = utc_now()
                    job.updated_at = utc_now()
                    await db.commit()
                    broadcast_status(job_id, {"status": "succeeded"})

                elif result.status == "unresolved":
                    job.status = "unresolved"
                    job.reasons = result.reasons
                    job.finished_at = utc_now()
                    job.updated_at = utc_now()
                    await db.commit()
                    broadcast_status(job_id, {"status": "unresolved", "reasons": job.reasons})

                else:
                    job.status = "failed"
                    job.error_code = result.error_code or "pipeline_failed"
                    job.reasons = result.reasons
                    job.finished_at = utc_now()
                    job.updated_at = utc_now()
                    await db.commit()
                    broadcast_status(job_id, {"status": "failed", "error_code": job.error_code})

        except asyncio.TimeoutError:
            logger.error(f"Job {job_id} exceeded overall timeout of {settings.JOB_TIMEOUT_SECONDS}s.")
            async with async_session_maker() as db:
                stmt = select(Job).where(Job.id == job_id)
                job = (await db.execute(stmt)).scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_code = "job_timeout"
                    job.finished_at = utc_now()
                    await db.commit()
            broadcast_status(job_id, {"status": "failed", "error_code": "job_timeout"})

        except asyncio.CancelledError:
            logger.info(f"Job {job_id} task was cancelled.")
            async with async_session_maker() as db:
                stmt = select(Job).where(Job.id == job_id)
                job = (await db.execute(stmt)).scalar_one_or_none()
                if job and job.status not in ("succeeded", "failed", "canceled"):
                    job.status = "canceled"
                    job.finished_at = utc_now()
                    await db.commit()
            broadcast_status(job_id, {"status": "canceled"})

        except Exception as e:
            logger.error(f"Unexpected error executing job {job_id}: {e}", exc_info=True)
            async with async_session_maker() as db:
                stmt = select(Job).where(Job.id == job_id)
                job = (await db.execute(stmt)).scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_code = "execution_error"
                    job.reasons = [{"message": str(e)}]
                    job.finished_at = utc_now()
                    await db.commit()
            broadcast_status(job_id, {"status": "failed", "error_code": "execution_error"})

        finally:
            # 6. Cleanup temp directory
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Could not remove temp dir {temp_dir}: {e}")
            _running_tasks.pop(job_id, None)


def dispatch_job(job_id: UUID, storage: StorageBackend, resume_payload: Optional[Dict[str, Any]] = None) -> asyncio.Task:
    """Spawns an asynchronous background task to execute or resume a job."""
    task = asyncio.create_task(execute_job(job_id, storage, resume_payload=resume_payload))
    _running_tasks[job_id] = task
    return task


async def recover_jobs_on_startup() -> None:
    """
    On server restart:
    Jobs in 'queued' or 'running' become 'failed' with error_code='server_restarted'.
    Waiting jobs ('needs_title_confirmation', 'needs_review') are preserved.
    """
    async with async_session_maker() as db:
        stmt = (
            update(Job)
            .where(Job.status.in_(["queued", "running"]))
            .values(
                status="failed",
                error_code="server_restarted",
                finished_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        res = await db.execute(stmt)
        await db.commit()
        if res.rowcount > 0:
            logger.info(f"Startup recovery: marked {res.rowcount} interrupted jobs as failed.")


async def run_periodic_maintenance() -> None:
    """
    Background worker that runs every 10 minutes:
    1. Expires waiting jobs older than INTERRUPT_EXPIRE_HOURS.
    2. Deletes finished jobs older than JOB_RETENTION_DAYS.
    """
    while True:
        try:
            await asyncio.sleep(600)  # Check every 10 minutes
            now = utc_now()

            async with async_session_maker() as db:
                # 1. Expiry check
                expire_cutoff = now - timedelta(hours=settings.INTERRUPT_EXPIRE_HOURS)
                expire_stmt = (
                    update(Job)
                    .where(
                        Job.status.in_(["needs_title_confirmation", "needs_review"]),
                        Job.updated_at < expire_cutoff,
                    )
                    .values(status="expired", finished_at=now, updated_at=now)
                )
                await db.execute(expire_stmt)

                # 2. Retention check
                retention_cutoff = now - timedelta(days=settings.JOB_RETENTION_DAYS)
                retention_stmt = delete(Job).where(
                    Job.status.in_(["succeeded", "unresolved", "failed", "canceled", "expired"]),
                    Job.finished_at < retention_cutoff,
                )
                await db.execute(retention_stmt)
                await db.commit()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error during periodic job maintenance: {e}")
