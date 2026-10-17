import logging
from typing import Any, Optional
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings

logger = logging.getLogger(__name__)

_checkpointer_instance: Optional[Any] = None


def get_checkpointer() -> Any:
    """
    Returns the configured checkpointer.
    Supports Postgres (persistent across restarts) or in-memory fallback.
    """
    global _checkpointer_instance
    if _checkpointer_instance is not None:
        return _checkpointer_instance

    mode = settings.CHECKPOINTER.lower().strip()

    if mode == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            # Use raw connection string without +psycopg driver for psycopg3 pool if required
            db_url = settings.CHECKPOINT_DATABASE_URL or settings.DATABASE_URL
            # Normalize to plain postgresql:// if needed
            raw_url = db_url.replace("postgresql+psycopg://", "postgresql://")
            _checkpointer_instance = PostgresSaver.from_conn_string(raw_url)
            logger.info("Using PostgreSQL checkpointer for LangGraph.")
            return _checkpointer_instance
        except ImportError:
            logger.warning(
                "langgraph-checkpoint-postgres is not installed. Falling back to MemorySaver."
            )
        except Exception as e:
            logger.error(f"Failed to initialize Postgres checkpointer: {e}. Falling back to MemorySaver.")

    # Default in-memory checkpointer
    logger.info("Using MemorySaver checkpointer for LangGraph.")
    _checkpointer_instance = MemorySaver()
    return _checkpointer_instance


async def setup_checkpointer() -> None:
    """
    Initializes checkpoint tables if using a persistent checkpointer.
    Called once during application lifespan startup.
    """
    cp = get_checkpointer()
    if hasattr(cp, "setup"):
        try:
            if callable(cp.setup):
                res = cp.setup()
                if hasattr(res, "__await__"):
                    await res
            logger.info("Checkpointer setup completed.")
        except Exception as e:
            logger.warning(f"Checkpointer setup notice: {e}")
