import logging
from typing import Any, Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings

logger = logging.getLogger(__name__)

_checkpointer_instance: Optional[Any] = None
_async_pool: Optional[Any] = None


def get_checkpointer() -> Any:
    """
    Returns the configured checkpointer.
    Supports AsyncPostgresSaver (persistent across restarts) or in-memory fallback.
    """
    global _checkpointer_instance
    if _checkpointer_instance is not None and isinstance(_checkpointer_instance, BaseCheckpointSaver):
        return _checkpointer_instance

    mode = settings.CHECKPOINTER.lower().strip()

    if mode == "postgres":
        try:
            from psycopg.rows import dict_row
            from psycopg_pool import AsyncConnectionPool
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            # Use raw connection string without +psycopg driver for psycopg3 pool if required
            db_url = settings.CHECKPOINT_DATABASE_URL or settings.DATABASE_URL
            raw_url = db_url.replace("postgresql+psycopg://", "postgresql://")

            pool = AsyncConnectionPool(
                conninfo=raw_url,
                max_size=settings.DB_POOL_SIZE or 10,
                open=False,
                kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            )
            _checkpointer_instance = AsyncPostgresSaver(pool)
            logger.info("Using PostgreSQL AsyncPostgresSaver checkpointer for LangGraph.")
            return _checkpointer_instance
        except ImportError:
            logger.warning(
                "langgraph-checkpoint-postgres or psycopg_pool is not installed. Falling back to MemorySaver."
            )
        except Exception as e:
            logger.error(f"Failed to initialize AsyncPostgresSaver: {e}. Falling back to MemorySaver.")

    # Default in-memory checkpointer
    logger.info("Using MemorySaver checkpointer for LangGraph.")
    _checkpointer_instance = MemorySaver()
    return _checkpointer_instance


async def setup_checkpointer() -> None:
    """
    Initializes checkpoint tables and connection pool if using a persistent checkpointer.
    Called once during application lifespan startup.
    """
    global _checkpointer_instance, _async_pool
    mode = settings.CHECKPOINTER.lower().strip()

    if mode == "postgres":
        try:
            from psycopg.rows import dict_row
            from psycopg_pool import AsyncConnectionPool
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            db_url = settings.CHECKPOINT_DATABASE_URL or settings.DATABASE_URL
            raw_url = db_url.replace("postgresql+psycopg://", "postgresql://")

            _async_pool = AsyncConnectionPool(
                conninfo=raw_url,
                max_size=settings.DB_POOL_SIZE or 10,
                open=False,
                kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            )
            await _async_pool.open()
            saver = AsyncPostgresSaver(_async_pool)
            await saver.setup()
            _checkpointer_instance = saver
            logger.info("AsyncPostgresSaver initialized and setup successfully.")
            return
        except Exception as e:
            logger.error(f"Failed to setup AsyncPostgresSaver: {e}. Falling back to MemorySaver.")

    _checkpointer_instance = MemorySaver()
    logger.info("Using MemorySaver checkpointer for LangGraph.")


async def close_checkpointer() -> None:
    """Closes the async connection pool on app shutdown."""
    global _async_pool
    if _async_pool is not None:
        try:
            await _async_pool.close()
        except Exception as e:
            logger.warning(f"Notice closing checkpointer pool: {e}")
        _async_pool = None
