import base64
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import utc_now
from app.db.models.file import File
from app.db.models.job import Job
from app.jobs.runner import broadcast_status, cancel_running_task, dispatch_job
from app.jobs.schemas import ResumeRequest
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ["queued", "running", "needs_title_confirmation", "needs_review"]
FINAL_STATUSES = ["succeeded", "unresolved", "failed", "canceled", "expired"]


class JobService:
    @classmethod
    async def create_job(
        cls,
        db: AsyncSession,
        storage: StorageBackend,
        owner_id: UUID,
        file_id: UUID,
        tex_mode: str = "standalone",
    ) -> Tuple[Job, bool]:
        """
        Creates or returns an active citation generation job for a file.
        Idempotent: returns (job, False) if active job exists (200), (job, True) if newly created (202).
        Enforces MAX_ACTIVE_JOBS_PER_USER limit (429).
        """
        # 1. Verify file exists and belongs to owner
        file_stmt = select(File).where(File.id == file_id, File.owner_id == owner_id)
        file_rec = (await db.execute(file_stmt)).scalar_one_or_none()
        if not file_rec:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "file_not_found", "message": "File not found.", "details": {}}},
            )

        # 2. Check if an active job already exists for this file (Idempotency)
        existing_stmt = select(Job).where(
            Job.file_id == file_id,
            Job.owner_id == owner_id,
            Job.status.in_(ACTIVE_STATUSES),
        )
        existing_job = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing_job:
            return existing_job, False

        # 3. Check active jobs per user limit
        count_stmt = select(func.count(Job.id)).where(
            Job.owner_id == owner_id,
            Job.status.in_(ACTIVE_STATUSES),
        )
        active_count = (await db.execute(count_stmt)).scalar() or 0
        if active_count >= settings.MAX_ACTIVE_JOBS_PER_USER:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "code": "too_many_active_jobs",
                        "message": f"Active job limit reached (max {settings.MAX_ACTIVE_JOBS_PER_USER}). Please wait for existing jobs to complete.",
                        "details": {},
                    }
                },
                headers={"Retry-After": "10"},
            )

        # 4. Insert new job
        new_job = Job(
            id=uuid4(),
            owner_id=owner_id,
            file_id=file_id,
            status="queued",
            tex_mode=tex_mode,
        )
        db.add(new_job)

        try:
            await db.commit()
            await db.refresh(new_job)
        except IntegrityError:
            # Partial unique index uq_jobs_file_active race condition backstop
            await db.rollback()
            existing_active = (await db.execute(existing_stmt)).scalar_one_or_none()
            if existing_active:
                return existing_active, False
            raise

        # 5. Dispatch background task
        dispatch_job(new_job.id, storage)
        return new_job, True

    @classmethod
    def _enrich_pending_interrupt(cls, job: Job) -> None:
        """Enrich missing journal_abbreviation in pending_interrupt or result_metadata if journal exists."""
        if not job:
            return
        try:
            from citegen.metadata.abbreviations import get_journal_abbreviation

            # 1. Enrich pending_interrupt
            if job.pending_interrupt and isinstance(job.pending_interrupt, dict):
                pi = dict(job.pending_interrupt)
                updated = False
                for key in ("selected_metadata", "record"):
                    rec = pi.get(key)
                    if isinstance(rec, dict) and not rec.get("journal_abbreviation") and rec.get("journal"):
                        abbr, _ = get_journal_abbreviation(rec["journal"])
                        if abbr:
                            rec = dict(rec)
                            rec["journal_abbreviation"] = abbr
                            pi[key] = rec
                            updated = True
                if updated:
                    job.pending_interrupt = pi

            # 2. Enrich result_metadata
            if job.result_metadata and isinstance(job.result_metadata, dict):
                rm = dict(job.result_metadata)
                if not rm.get("journal_abbreviation") and rm.get("journal"):
                    abbr, _ = get_journal_abbreviation(rm["journal"])
                    if abbr:
                        rm["journal_abbreviation"] = abbr
                        job.result_metadata = rm
        except Exception as e:
            logger.debug("Failed to enrich job abbreviation: %s", e)

    @classmethod
    async def get_job(cls, db: AsyncSession, owner_id: UUID, job_id: UUID) -> Job:
        """Fetches a job owned by owner_id or raises 404."""
        stmt = select(Job).where(Job.id == job_id, Job.owner_id == owner_id)
        job = (await db.execute(stmt)).scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "job_not_found", "message": "Job not found.", "details": {}}},
            )
        cls._enrich_pending_interrupt(job)
        return job

    @classmethod
    async def list_jobs(
        cls,
        db: AsyncSession,
        owner_id: UUID,
        file_id: Optional[UUID] = None,
        limit: int = 200,
        cursor: Optional[str] = None,
    ) -> Tuple[List[Job], Optional[str]]:
        """
        Lists jobs owned by owner_id, optionally filtered by file_id.
        Sorted by created_at desc, id desc with cursor pagination.
        """
        limit = max(1, min(limit, 500))
        query = select(Job).where(Job.owner_id == owner_id)

        if file_id is not None:
            query = query.where(Job.file_id == file_id)

        if cursor:
            try:
                decoded = base64.b64decode(cursor.encode("utf-8")).decode("utf-8")
                created_iso, c_id = decoded.split("|")
                c_created = datetime.fromisoformat(created_iso)
                c_uuid = UUID(c_id)
                query = query.where(
                    or_(
                        Job.created_at < c_created,
                        and_(Job.created_at == c_created, Job.id < c_uuid),
                    )
                )
            except Exception as e:
                logger.warning(f"Invalid cursor format '{cursor}': {e}")

        query = query.order_by(Job.created_at.desc(), Job.id.desc()).limit(limit + 1)
        res = await db.execute(query)
        rows = list(res.scalars().all())

        next_cursor = None
        if len(rows) > limit:
            last_item = rows[limit - 1]
            raw_cursor = f"{last_item.created_at.isoformat()}|{last_item.id}"
            next_cursor = base64.b64encode(raw_cursor.encode("utf-8")).decode("utf-8")
            rows = rows[:limit]

        for r in rows:
            cls._enrich_pending_interrupt(r)

        return rows, next_cursor

    @classmethod
    async def resume_job(
        cls,
        db: AsyncSession,
        storage: StorageBackend,
        owner_id: UUID,
        job_id: UUID,
        resume_data: ResumeRequest,
    ) -> Job:
        """
        Resumes a paused job with validated user review response.
        Enforces 409 wrong_interrupt_kind and 409 job_not_waiting.
        """
        job = await cls.get_job(db, owner_id, job_id)

        if job.status not in ("needs_title_confirmation", "needs_review"):
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "job_not_waiting", "message": "Job is not waiting for user input.", "details": {}}},
            )

        # Validate action against interrupt kind
        pending_kind = (job.pending_interrupt or {}).get("kind")
        if job.status == "needs_title_confirmation":
            if resume_data.action not in ("select", "custom", "skip"):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": {
                            "code": "wrong_interrupt_kind",
                            "message": f"Action '{resume_data.action}' is not valid for title confirmation (select, custom, skip).",
                            "details": {},
                        }
                    },
                )
        elif job.status == "needs_review":
            if resume_data.action not in ("accept", "edit", "skip"):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": {
                            "code": "wrong_interrupt_kind",
                            "message": f"Action '{resume_data.action}' is not valid for metadata review (accept, edit, skip).",
                            "details": {},
                        }
                    },
                )

        # Atomically update status to queued to prevent double resume race conditions
        update_stmt = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.owner_id == owner_id,
                Job.status.in_(["needs_title_confirmation", "needs_review"]),
            )
            .values(
                status="queued",
                pending_interrupt=None,
                updated_at=utc_now(),
            )
        )
        res = await db.execute(update_stmt)
        await db.commit()

        if res.rowcount == 0:
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "job_not_waiting", "message": "Job is no longer waiting for user input.", "details": {}}},
            )

        # Build resume payload
        if resume_data.action == "select":
            resume_payload = {"action": "select", "index": resume_data.index}
        elif resume_data.action == "custom":
            resume_payload = {"action": "custom", "title": resume_data.title}
        elif resume_data.action == "accept":
            resume_payload = {"action": "accept"}
        elif resume_data.action == "edit":
            resume_payload = {"action": "edit", "edits": resume_data.edits}
        elif resume_data.action == "skip":
            resume_payload = {"action": "skip"}
        else:
            resume_payload = {"action": resume_data.action}

        # Dispatch background task to continue execution
        dispatch_job(job_id, storage, resume_payload=resume_payload)
        broadcast_status(job_id, {"status": "queued"})

        # Return refreshed job
        return await cls.get_job(db, owner_id, job_id)

    @classmethod
    async def cancel_job(cls, db: AsyncSession, owner_id: UUID, job_id: UUID) -> Job:
        """
        Cancels an active job. Returns 409 if already in a final status.
        """
        job = await cls.get_job(db, owner_id, job_id)

        if job.status in FINAL_STATUSES:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": {
                        "code": "job_already_finished",
                        "message": f"Cannot cancel job in final status '{job.status}'.",
                        "details": {},
                    }
                },
            )

        cancel_running_task(job_id)

        job.status = "canceled"
        job.finished_at = utc_now()
        job.updated_at = utc_now()
        await db.commit()
        await db.refresh(job)

        broadcast_status(job_id, {"status": "canceled"})
        return job

    @classmethod
    async def get_job_tex(cls, db: AsyncSession, owner_id: UUID, job_id: UUID) -> Tuple[str, str]:
        """
        Fetches generated .tex content and sanitized filename for a succeeded job.
        Raises 409 if job does not have a .tex result.
        """
        job = await cls.get_job(db, owner_id, job_id)

        if job.status != "succeeded" or not job.result_tex:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": {
                        "code": "no_tex_result",
                        "message": f"Job is in status '{job.status}' and has no generated .tex result.",
                        "details": {},
                    }
                },
            )

        # Get original file name to build sanitized attachment name
        file_stmt = select(File).where(File.id == job.file_id)
        file_rec = (await db.execute(file_stmt)).scalar_one_or_none()
        raw_name = file_rec.name if file_rec else "citation"

        # Sanitize filename: avoid header injection / path traversal
        clean_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", raw_name)
        if clean_name.lower().endswith(f".{file_rec.ext.lower()}") if file_rec else clean_name.lower().endswith(".pdf"):
            clean_name = clean_name.rsplit(".", 1)[0]
        tex_filename = f"{clean_name}.tex"

        return job.result_tex, tex_filename
