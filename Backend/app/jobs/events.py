import asyncio
import json
import logging
from typing import AsyncGenerator
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.job import Job
from app.jobs.runner import register_listener, unregister_listener
from app.jobs.service import FINAL_STATUSES, JobService

logger = logging.getLogger(__name__)


async def job_event_generator(
    job_id: UUID,
    initial_job: Job,
) -> AsyncGenerator[str, None]:
    """
    Asynchronous SSE generator:
    1. Emits initial job state.
    2. Streams real-time status transitions.
    3. Emits periodic heartbeat comments (': heartbeat\\n\\n') every SSE_HEARTBEAT_SECONDS.
    4. Automatically closes when job reaches a terminal/final state.
    """
    # 1. Emit current state immediately upon connection
    init_data = {
        "status": initial_job.status,
        "pending_interrupt": initial_job.pending_interrupt,
        "error_code": initial_job.error_code,
    }
    yield f"data: {json.dumps(init_data)}\n\n"

    # If already in final state, close stream immediately
    if initial_job.status in FINAL_STATUSES:
        return

    # 2. Register listener queue for live events
    queue = register_listener(job_id)
    try:
        while True:
            try:
                event_data = await asyncio.wait_for(
                    queue.get(),
                    timeout=float(settings.SSE_HEARTBEAT_SECONDS),
                )
                yield f"data: {json.dumps(event_data)}\n\n"

                # Check if terminal state reached
                if event_data.get("status") in FINAL_STATUSES:
                    break

            except asyncio.TimeoutError:
                # SSE specification heartbeat comment
                yield ": heartbeat\n\n"

    except asyncio.CancelledError:
        # Client disconnected
        pass
    finally:
        unregister_listener(job_id, queue)
