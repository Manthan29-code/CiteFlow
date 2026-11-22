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
from app.db.models.folder import Folder
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
        style_id: Optional[UUID] = None,
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

        # 4. Remove previous non-active jobs for this file so only the latest action is stored in DB
        from sqlalchemy import delete
        await db.execute(
            delete(Job).where(
                Job.file_id == file_id,
                Job.owner_id == owner_id,
                Job.status.notin_(ACTIVE_STATUSES),
            )
        )

        # 5. Insert new job
        new_job = Job(
            id=uuid4(),
            owner_id=owner_id,
            file_id=file_id,
            style_id=style_id,
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

        # 6. Dispatch background task
        dispatch_job(new_job.id, storage)
        return new_job, True

    @classmethod
    async def create_folder_jobs(
        cls,
        db: AsyncSession,
        storage: StorageBackend,
        owner_id: UUID,
        folder_id: UUID,
        tex_mode: str = "standalone",
        style_id: Optional[UUID] = None,
        force: bool = False,
    ) -> List[Job]:
        """
        Creates or returns citation generation jobs for all PDF files in folder_id.
        Skips files that already have an active or succeeded citation job (unless force=True).
        """
        stmt = (
            select(File)
            .where(File.folder_id == folder_id, File.owner_id == owner_id, File.ext == "pdf")
            .order_by(File.name.asc())
        )
        files = list((await db.execute(stmt)).scalars().all())
        if not files:
            return []

        jobs: List[Job] = []
        for file_rec in files:
            try:
                # If not forcing, check if file already has succeeded job
                if not force:
                    succ_stmt = (
                        select(Job)
                        .where(
                            Job.file_id == file_rec.id,
                            Job.owner_id == owner_id,
                            Job.status == "succeeded",
                        )
                        .order_by(Job.created_at.desc(), Job.id.desc())
                        .limit(1)
                    )
                    existing_succ = (await db.execute(succ_stmt)).scalars().first()
                    if existing_succ:
                        cls._enrich_pending_interrupt(existing_succ)
                        jobs.append(existing_succ)
                        continue

                job, _ = await cls.create_job(
                    db=db,
                    storage=storage,
                    owner_id=owner_id,
                    file_id=file_rec.id,
                    tex_mode=tex_mode,
                    style_id=style_id,
                )
                cls._enrich_pending_interrupt(job)
                jobs.append(job)
            except HTTPException as e:
                if e.status_code == 429:
                    logger.warning(
                        f"Batch folder job limit reached for user {owner_id} at file {file_rec.id}: {e.detail}"
                    )
                    break
                raise
        return jobs

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

        seen_files = set()
        deduped_rows = []
        for r in rows:
            if r.file_id not in seen_files:
                seen_files.add(r.file_id)
                cls._enrich_pending_interrupt(r)
                deduped_rows.append(r)

        return deduped_rows, next_cursor

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
            if resume_data.title:
                resume_payload["title"] = resume_data.title
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
    async def transform_job_style(
        cls,
        db: AsyncSession,
        owner_id: UUID,
        job_id: UUID,
        style_id: Optional[UUID] = None,
    ) -> Job:
        """
        Transforms the citation style of an already-succeeded job.
        Uses cached result_metadata and formats new result_tex instantaneously (<10ms).
        """
        job = await cls.get_job(db, owner_id, job_id)
        if job.status != "succeeded" or not job.result_metadata:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "cannot_transform_style",
                        "message": "Only succeeded jobs with verified metadata can be transformed.",
                        "details": {},
                    }
                },
            )

        template: Optional[str] = None
        if style_id:
            from app.db.models.citation_style import CitationStyle

            stmt = select(CitationStyle).where(
                CitationStyle.id == style_id,
                or_(CitationStyle.is_builtin.is_(True), CitationStyle.owner_id == owner_id),
            )
            style_rec = (await db.execute(stmt)).scalar_one_or_none()
            if not style_rec:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": {
                            "code": "style_not_found",
                            "message": f"Citation style '{style_id}' not found.",
                            "details": {},
                        }
                    },
                )
            template = style_rec.template

        from citegen.api import render_single_record

        rendered_tex = render_single_record(
            metadata=job.result_metadata,
            template=template,
            standalone=(job.tex_mode == "standalone"),
        )

        job.style_id = style_id
        job.result_tex = rendered_tex
        job.updated_at = utc_now()
        await db.commit()
        await db.refresh(job)
        cls._enrich_pending_interrupt(job)
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

    @classmethod
    async def get_folder_tex(
        cls,
        db: AsyncSession,
        owner_id: UUID,
        folder_id: UUID,
        style_id: Optional[UUID] = None,
    ) -> Tuple[str, str]:
        """
        Gathers all succeeded citation jobs for files in folder_id,
        renders each citation with its own \\begin{thebibliography}{99} block,
        and wraps them in a standalone document.
        Returns (tex_content, filename).
        """
        # 1. Verify folder exists and belongs to owner
        folder_stmt = select(Folder).where(Folder.id == folder_id, Folder.owner_id == owner_id)
        folder = (await db.execute(folder_stmt)).scalar_one_or_none()
        if not folder:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "folder_not_found", "message": "Folder not found.", "details": {}}},
            )

        # 2. Get all files in this folder
        files_stmt = select(File).where(File.folder_id == folder_id, File.owner_id == owner_id)
        files = list((await db.execute(files_stmt)).scalars().all())
        file_ids = [f.id for f in files]

        if not file_ids:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "no_citations", "message": "No files found in folder.", "details": {}}},
            )

        # 3. Get latest succeeded job for each file
        jobs_stmt = (
            select(Job)
            .where(Job.file_id.in_(file_ids), Job.owner_id == owner_id, Job.status == "succeeded")
            .order_by(Job.created_at.asc())
        )
        all_jobs = list((await db.execute(jobs_stmt)).scalars().all())

        latest_jobs_by_file: Dict[UUID, Job] = {}
        for j in all_jobs:
            latest_jobs_by_file[j.file_id] = j

        succeeded_jobs = list(latest_jobs_by_file.values())
        if not succeeded_jobs:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "no_succeeded_citations", "message": "No succeeded citations in this folder.", "details": {}}},
            )

        # 4. If style_id provided, get template
        template: Optional[str] = None
        if style_id:
            from app.db.models.citation_style import CitationStyle
            stmt = select(CitationStyle).where(
                CitationStyle.id == style_id,
                or_(CitationStyle.is_builtin.is_(True), CitationStyle.owner_id == owner_id),
            )
            style_rec = (await db.execute(stmt)).scalar_one_or_none()
            if style_rec:
                template = style_rec.template

        from citegen.latex.style_engine import format_bibitem_with_style
        from citegen.latex.citation_keys import generate_base_citation_key
        from citegen.metadata.models import ArticleMetadata
        from citegen.api import render_single_record

        bibitems: List[str] = []
        needs_commit = False
        for j in succeeded_jobs:
            if template and j.result_metadata:
                meta = ArticleMetadata(**j.result_metadata)
                key = generate_base_citation_key(meta)
                item = format_bibitem_with_style(meta, template, citation_key=key)
                bibitems.append(item)

                # Unify individual job in DB to this style
                if j.style_id != style_id:
                    j.style_id = style_id
                    j.result_tex = render_single_record(meta, template=template, standalone=(j.tex_mode == "standalone"))
                    j.updated_at = utc_now()
                    db.add(j)
                    needs_commit = True
            elif j.result_tex:
                # Extract the \bibitem from existing result_tex
                match = re.search(r"(\\bibitem\{[^}]+\}.*?)(?=\\end\{thebibliography\}|\Z)", j.result_tex, re.DOTALL)
                if match:
                    bibitems.append(match.group(1).strip())
                else:
                    bibitems.append(j.result_tex.strip())

        if needs_commit:
            try:
                await db.commit()
            except Exception:
                await db.rollback()

        # Join individual clean citations with an empty line
        clean_bibitems: List[str] = []
        for b in bibitems:
            m = re.search(r"(\\bibitem\{[^}]+\}.*?)(?=\\end\{thebibliography\}|\\end\{document\}|\Z)", b, re.DOTALL)
            if m:
                clean_bibitems.append(m.group(1).strip())
            else:
                clean_bibitems.append(b.strip())

        grouped_tex = "\n\n".join(clean_bibitems) + "\n"

        clean_folder = re.sub(r"[^a-zA-Z0-9_\-]", "_", folder.name) or "citations"
        filename = f"{clean_folder}_citations.tex"
        return grouped_tex, filename

    @classmethod
    async def transform_folder_jobs(
        cls,
        db: AsyncSession,
        owner_id: UUID,
        folder_id: UUID,
        style_id: Optional[UUID] = None,
    ) -> List[Job]:
        """
        Transforms all succeeded jobs for files in folder_id to style_id.
        Returns the list of updated jobs.
        """
        files_stmt = select(File).where(File.folder_id == folder_id, File.owner_id == owner_id)
        files = list((await db.execute(files_stmt)).scalars().all())
        file_ids = [f.id for f in files]

        if not file_ids:
            return []

        jobs_stmt = (
            select(Job)
            .where(Job.file_id.in_(file_ids), Job.owner_id == owner_id, Job.status == "succeeded")
            .order_by(Job.created_at.asc())
        )
        all_jobs = list((await db.execute(jobs_stmt)).scalars().all())

        latest_jobs_by_file: Dict[UUID, Job] = {}
        for j in all_jobs:
            latest_jobs_by_file[j.file_id] = j

        template: Optional[str] = None
        if style_id:
            from app.db.models.citation_style import CitationStyle
            stmt = select(CitationStyle).where(
                CitationStyle.id == style_id,
                or_(CitationStyle.is_builtin.is_(True), CitationStyle.owner_id == owner_id),
            )
            style_rec = (await db.execute(stmt)).scalar_one_or_none()
            if not style_rec:
                raise HTTPException(
                    status_code=404,
                    detail={"error": {"code": "style_not_found", "message": f"Citation style '{style_id}' not found.", "details": {}}},
                )
            template = style_rec.template

        from citegen.api import render_single_record

        updated_jobs: List[Job] = []
        for job in latest_jobs_by_file.values():
            if not job.result_metadata:
                continue
            rendered_tex = render_single_record(
                metadata=job.result_metadata,
                template=template,
                standalone=(job.tex_mode == "standalone"),
            )
            job.style_id = style_id
            job.result_tex = rendered_tex
            job.updated_at = utc_now()
            db.add(job)
            updated_jobs.append(job)

        if updated_jobs:
            await db.commit()
            for j in updated_jobs:
                await db.refresh(j)
                cls._enrich_pending_interrupt(j)

        return updated_jobs
