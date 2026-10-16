import asyncio
import logging
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.deletion import StorageDeletion
from app.db.session import async_session_maker
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

# Event used to immediately wake the cleaner when new deletions are enqueued
_cleaner_wake_event: asyncio.Event | None = None


def get_cleaner_wake_event() -> asyncio.Event:
    global _cleaner_wake_event
    if _cleaner_wake_event is None:
        _cleaner_wake_event = asyncio.Event()
    return _cleaner_wake_event


def wake_cleaner() -> None:
    """Signals the storage cleaner to process the deletion outbox immediately."""
    evt = get_cleaner_wake_event()
    evt.set()


async def process_storage_deletions_batch(
    session: AsyncSession, storage: StorageBackend
) -> int:
    """
    Selects up to STORAGE_CLEANER_BATCH_SIZE pending deletions using FOR UPDATE SKIP LOCKED,
    invokes storage.delete_many(), and removes succeeded rows or increments attempts for failures.
    Returns the count of processed rows.
    """
    # 1. Fetch batch with SKIP LOCKED where attempts < STORAGE_CLEANER_MAX_ATTEMPTS
    stmt = (
        select(StorageDeletion)
        .where(StorageDeletion.attempts < settings.STORAGE_CLEANER_MAX_ATTEMPTS)
        .order_by(StorageDeletion.id.asc())
        .limit(settings.STORAGE_CLEANER_BATCH_SIZE)
        .with_for_update(skip_locked=True)
    )
    res = await session.execute(stmt)
    records = list(res.scalars().all())

    if not records:
        return 0

    id_to_record = {r.imagekit_file_id: r for r in records}
    file_ids = list(id_to_record.keys())

    # 2. Invoke storage deletion
    try:
        delete_result = await storage.delete_many(file_ids)
    except Exception as ex:
        logger.error(f"Unexpected error calling delete_many on storage: {ex}", exc_info=True)
        # Mark all in this batch with an incremented attempt
        for rec in records:
            rec.attempts += 1
            rec.last_error = f"Storage exception: {str(ex)[:500]}"
            if rec.attempts >= settings.STORAGE_CLEANER_MAX_ATTEMPTS:
                logger.error(
                    f"Storage deletion reached max attempts for file_id {rec.imagekit_file_id}"
                )
        await session.commit()
        return len(records)

    # 3. Handle successes
    succeeded_file_ids = delete_result.succeeded
    succeeded_record_ids = [
        id_to_record[fid].id for fid in succeeded_file_ids if fid in id_to_record
    ]

    if succeeded_record_ids:
        del_stmt = delete(StorageDeletion).where(StorageDeletion.id.in_(succeeded_record_ids))
        await session.execute(del_stmt)

    # 4. Handle failures
    for fid, error_msg in delete_result.failed.items():
        if fid in id_to_record:
            rec = id_to_record[fid]
            rec.attempts += 1
            rec.last_error = error_msg[:500]
            if rec.attempts >= settings.STORAGE_CLEANER_MAX_ATTEMPTS:
                logger.error(
                    f"Storage deletion reached max attempts ({rec.attempts}) for file_id {fid}: {error_msg}"
                )

    await session.commit()
    return len(records)


class StorageCleanerWorker:
    """
    Background worker that continuously drains the deletion outbox.
    Runs periodically and responds to wake events.
    """

    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Storage cleaner worker started.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Storage cleaner worker stopped.")

    async def _run_loop(self) -> None:
        wake_event = get_cleaner_wake_event()

        while self._running:
            try:
                # Drain until empty
                has_more = True
                while has_more and self._running:
                    async with async_session_maker() as session:
                        count = await process_storage_deletions_batch(session, self.storage)
                        has_more = count >= settings.STORAGE_CLEANER_BATCH_SIZE

                # Wait for next interval or wake signal
                try:
                    await asyncio.wait_for(
                        wake_event.wait(),
                        timeout=settings.STORAGE_CLEANER_INTERVAL_SECONDS,
                    )
                    wake_event.clear()
                except asyncio.TimeoutError:
                    pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in storage cleaner loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Backoff before retrying loop
