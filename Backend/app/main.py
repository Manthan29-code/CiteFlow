import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# On Windows, Psycopg 3 async requires WindowsSelectorEventLoopPolicy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .auth.router import router as auth_router
from .core.config import settings
from .core.deps import get_storage
from .core.errors import (
    AppError,
    app_error_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from .core.logging import setup_logging
from .core.middleware import (
    RequestIdAndSecurityHeadersMiddleware,
    UploadSizeLimitMiddleware,
)
from .db.session import engine
from .files.router import router as files_router
from .folders.router import router as folders_router
from .jobs.checkpointer import setup_checkpointer, close_checkpointer
from .jobs.router import router as jobs_router
from .citation_styles.router import router as citation_styles_router
from .jobs.runner import recover_jobs_on_startup, run_periodic_maintenance
from .storage.cleaner import StorageCleanerWorker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 1. Setup logging
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting CiteFlow Backend...")

    # 2. Validate configuration at startup
    try:
        settings.validate_runtime()
        logger.info("Runtime settings validated successfully.")
    except Exception as e:
        logger.critical(f"Settings validation failed: {e}")
        raise

    if not settings.CROSSREF_MAILTO and settings.ENV == "production":
        logger.warning("CROSSREF_MAILTO is empty in production. Polite pool will not be used.")

    # 3. Verify DB connectivity (Fast, clean ping)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established successfully.")
    except Exception as e:
        logger.error(f"[DB ERROR] Failed to connect to PostgreSQL database: {e}", exc_info=True)
        logger.error("[DB ERROR] Please check DATABASE_URL in your .env and verify your Neon DB is reachable.")

    # 4. Initialize LangGraph checkpointer tables
    try:
        await setup_checkpointer()
        logger.info("Checkpointer setup completed.")
    except Exception as e:
        logger.error(f"Failed to setup checkpointer: {e}", exc_info=True)

    # 5. Recover orphaned jobs from previous server crash/restart
    try:
        await recover_jobs_on_startup()
    except Exception as e:
        logger.error(f"Error during job recovery on startup: {e}")

    # 6. Start background workers
    cleaner_worker = StorageCleanerWorker(get_storage())
    await cleaner_worker.start()

    maintenance_task = asyncio.create_task(run_periodic_maintenance())

    yield

    # Shutdown
    logger.info("Shutting down CiteFlow Backend...")
    maintenance_task.cancel()
    try:
        await maintenance_task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"Error during maintenance task cancellation: {e}")

    await cleaner_worker.stop()
    await close_checkpointer()
    await engine.dispose()
    logger.info("CiteFlow Backend shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="CiteFlow API",
        version="0.1.0",
        description="FastAPI Backend for CiteFlow (Citation & PDF Management)",
        lifespan=lifespan,
    )

    # Register Exception Handlers
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Middleware (Outer to Inner)
    # 1. Request ID and security headers (nosniff)
    app.add_middleware(RequestIdAndSecurityHeadersMiddleware)
    # 2. Upload size limit ASGI middleware
    app.add_middleware(UploadSizeLimitMiddleware)
    # 3. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-CSRF-Token", "X-Request-ID"],
    )

    # Health check endpoints outside /api/v1
    @app.get("/health", tags=["health"], operation_id="health_liveness")
    async def health_liveness():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"], operation_id="health_readiness")
    async def health_readiness():
        # Check DB
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            raise AppError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="database_unavailable",
                message=f"Database connectivity check failed: {str(e)}",
            )
        return {"status": "ready"}

    # Include API Routers under /api/v1
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(folders_router, prefix="/api/v1")
    app.include_router(files_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(citation_styles_router, prefix="/api/v1")

    return app


app = create_app()

