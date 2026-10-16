from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    AppError,
    ConflictError,
    InvalidCredentialsError,
    RegistrationDisabledError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.base import utc_now
from app.db.models.folder import Folder
from app.db.models.user import RefreshToken, User

# Dummy hash for timing attack mitigation
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQAAAAAAAAAAA$q7Lz67tTzLq/iY50K6d7s3zS2o5Wc3iYm4m6U8k6H5o"


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, email: str, password: str) -> User:
        """Registers a new user and creates their unique root folder in the same transaction."""
        if not settings.ALLOW_REGISTRATION:
            raise RegistrationDisabledError()

        normalized_email = email.strip().lower()

        if len(password) < settings.PASSWORD_MIN_LENGTH:
            raise AppError(
                status_code=422,
                code="validation_error",
                message=f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long.",
            )

        # Check existing email
        stmt = select(User).where(func.lower(User.email) == normalized_email)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ConflictError("An account with this email address already exists.", code="email_conflict")

        user = User(
            id=uuid4(),
            email=normalized_email,
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(user)

        # Create user's single root folder (parent_id is None)
        root_folder = Folder(
            id=uuid4(),
            owner_id=user.id,
            parent_id=None,
            name="root",
        )
        db.add(root_folder)

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def login(
        db: AsyncSession, email: str, password: str
    ) -> tuple[User, str, str, str]:
        """
        Authenticates user, creates fresh tokens and returns (user, access_token, refresh_token, csrf_token).
        Mitigates timing attacks with constant-time check.
        """
        normalized_email = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == normalized_email)
        user = (await db.execute(stmt)).scalar_one_or_none()

        if not user or not user.is_active:
            # Constant-time verify against dummy hash
            verify_password(password, DUMMY_HASH)
            raise InvalidCredentialsError()

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        # Generate tokens
        access_token = create_access_token(user.id)
        raw_refresh = generate_refresh_token()
        csrf_token = generate_csrf_token()

        family_id = uuid4()
        expires_at = utc_now() + timedelta(days=settings.REFRESH_TOKEN_DAYS)

        refresh_row = RefreshToken(
            id=uuid4(),
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            family_id=family_id,
            expires_at=expires_at,
        )
        db.add(refresh_row)
        await db.commit()

        return user, access_token, raw_refresh, csrf_token

    @staticmethod
    async def refresh(db: AsyncSession, raw_refresh_token: str) -> tuple[str, str]:
        """
        Rotates refresh token. If a revoked token is presented, revokes entire family (theft detection).
        Returns (new_access_token, new_raw_refresh_token).
        """
        if not raw_refresh_token:
            raise UnauthorizedError("Missing refresh token.", code="invalid_token")

        token_hash = hash_refresh_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        token_record = (await db.execute(stmt)).scalar_one_or_none()

        if not token_record:
            raise UnauthorizedError("Invalid refresh token.", code="invalid_token")

        now = utc_now()

        # Token theft detection: reusing an already revoked token
        if token_record.revoked_at is not None:
            # Revoke entire family!
            revoke_all_stmt = (
                update(RefreshToken)
                .where(RefreshToken.family_id == token_record.family_id)
                .values(revoked_at=now)
            )
            await db.execute(revoke_all_stmt)
            await db.commit()
            raise UnauthorizedError("Token reuse detected. Session invalidated.", code="token_theft")

        # Check expiration
        if token_record.expires_at < now:
            raise UnauthorizedError("Refresh token has expired.", code="token_expired")

        # Revoke current token
        token_record.revoked_at = now

        # Issue new token in same family
        new_raw_refresh = generate_refresh_token()
        new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_DAYS)
        new_record = RefreshToken(
            id=uuid4(),
            user_id=token_record.user_id,
            token_hash=hash_refresh_token(new_raw_refresh),
            family_id=token_record.family_id,
            expires_at=new_expires_at,
        )
        db.add(new_record)

        new_access_token = create_access_token(token_record.user_id)
        await db.commit()

        return new_access_token, new_raw_refresh

    @staticmethod
    async def logout(db: AsyncSession, raw_refresh_token: str | None) -> None:
        """Revokes the refresh token family."""
        if not raw_refresh_token:
            return

        token_hash = hash_refresh_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        token_record = (await db.execute(stmt)).scalar_one_or_none()

        if token_record:
            now = utc_now()
            revoke_all_stmt = (
                update(RefreshToken)
                .where(RefreshToken.family_id == token_record.family_id)
                .values(revoked_at=now)
            )
            await db.execute(revoke_all_stmt)
            await db.commit()
