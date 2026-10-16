from typing import Annotated, Optional
from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import LoginRequest, MessageResponse, RegisterRequest, UserResponse
from .service import AuthService
from ..core.config import settings
from ..core.deps import check_csrf, get_current_user, get_db
from ..core.limits import get_client_ip, limiter
from ..db.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: Optional[str] = None,
) -> None:
    """Sets standard auth and CSRF cookies per security specifications."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_DAYS * 86400,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        path="/api/v1/auth",
    )
    if csrf_token:
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            max_age=settings.REFRESH_TOKEN_DAYS * 86400,
            httponly=False,  # Frontend reads this to send in X-CSRF-Token header
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            domain=settings.COOKIE_DOMAIN or None,
            path="/",
        )


def clear_auth_cookies(response: Response) -> None:
    """Clears all session and auth cookies."""
    response.delete_cookie(key="access_token", path="/", domain=settings.COOKIE_DOMAIN or None)
    response.delete_cookie(key="refresh_token", path="/api/v1/auth", domain=settings.COOKIE_DOMAIN or None)
    response.delete_cookie(key="csrf_token", path="/", domain=settings.COOKIE_DOMAIN or None)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="auth_register",
)
async def register(
    request: Request,
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    ip = get_client_ip(request)
    limiter.check(f"register_ip:{ip}", settings.REGISTER_RATE_LIMIT)

    user = await AuthService.register(db, body.email, body.password)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=UserResponse,
    operation_id="auth_login",
)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    ip = get_client_ip(request)
    limiter.check(f"login_ip:{ip}", settings.LOGIN_RATE_LIMIT)
    limiter.check(f"login_email:{body.email.strip().lower()}", settings.LOGIN_RATE_LIMIT)

    user, access_token, refresh_token, csrf_token = await AuthService.login(
        db, body.email, body.password
    )
    set_auth_cookies(response, access_token, refresh_token, csrf_token)
    response.headers["Cache-Control"] = "no-store"
    return UserResponse.model_validate(user)


@router.post(
    "/refresh",
    response_model=MessageResponse,
    operation_id="auth_refresh",
)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Optional[str] = Cookie(default=None),
) -> MessageResponse:
    new_access, new_refresh = await AuthService.refresh(db, refresh_token or "")
    set_auth_cookies(response, new_access, new_refresh)
    response.headers["Cache-Control"] = "no-store"
    return MessageResponse(message="Token rotated successfully.")


@router.post(
    "/logout",
    response_model=MessageResponse,
    dependencies=[Depends(check_csrf)],
    operation_id="auth_logout",
)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Optional[str] = Cookie(default=None),
) -> MessageResponse:
    await AuthService.logout(db, refresh_token)
    clear_auth_cookies(response)
    response.headers["Cache-Control"] = "no-store"
    return MessageResponse(message="Logged out successfully.")


@router.get(
    "/me",
    response_model=UserResponse,
    operation_id="auth_get_me",
)
async def get_me(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    response.headers["Cache-Control"] = "no-store"
    return UserResponse.model_validate(current_user)
