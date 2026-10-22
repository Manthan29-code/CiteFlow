from typing import Annotated, Optional
from uuid import UUID
from fastapi import Cookie, Depends, Header, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import CsrfFailedError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db
from app.storage.base import StorageBackend
from app.storage.fake_storage import FakeStorage
from app.storage.imagekit_storage import ImageKitStorage

# Global default storage instance
_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Dependency returning the StorageBackend. Overrideable in tests."""
    global _storage_instance
    if _storage_instance is None:
        if settings.IMAGEKIT_PRIVATE_KEY and "your_" not in settings.IMAGEKIT_URL_ENDPOINT:
            _storage_instance = ImageKitStorage()
        else:
            _storage_instance = FakeStorage()
    return _storage_instance


def set_storage_backend(backend: StorageBackend) -> None:
    global _storage_instance
    _storage_instance = backend


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> User:
    """
    Extracts access token from cookie (preferred) or Authorization header.
    Validates token and returns active User instance.
    """
    token = access_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if not token:
        raise UnauthorizedError(message="Authentication credentials were not provided.")

    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedError(message="Invalid token payload.")
        user_id = UUID(user_id_str)
    except Exception as e:
        raise UnauthorizedError(message="Invalid or expired access token.", code="invalid_token")

    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError(message="User not found or inactive.", code="unauthorized")

    return user


async def check_csrf(
    request: Request,
    x_csrf_token: Optional[str] = Header(default=None, alias="X-CSRF-Token"),
    csrf_token: Optional[str] = Cookie(default=None),
) -> None:
    """
    Double-submit CSRF verification for state-changing HTTP requests.
    Exempts GET, HEAD, OPTIONS and initial auth endpoints (login, register, csrf).
    Supports cross-origin SPA deployments where cookies and headers are synchronized.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    path = request.url.path
    if path in ("/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/csrf"):
        return

    if not x_csrf_token:
        raise CsrfFailedError("CSRF token missing in request header.")

    if csrf_token and x_csrf_token != csrf_token:
        raise CsrfFailedError("CSRF token does not match cookie.")

    if not csrf_token:
        origin = request.headers.get("origin")
        if not origin or origin not in settings.cors_origins_list:
            raise CsrfFailedError("CSRF token missing or incorrect.")
