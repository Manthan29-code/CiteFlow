from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.details = details or {}


# Convenience specialized exceptions
class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required.", code: str = "unauthorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(status.HTTP_401_UNAUTHORIZED, code, message, details)


class InvalidCredentialsError(AppError):
    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "invalid_credentials", message)


class CsrfFailedError(AppError):
    def __init__(self, message: str = "CSRF verification failed."):
        super().__init__(status.HTTP_403_FORBIDDEN, "csrf_failed", message)


class RegistrationDisabledError(AppError):
    def __init__(self, message: str = "User registration is currently disabled."):
        super().__init__(status.HTTP_403_FORBIDDEN, "registration_disabled", message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.", code: str = "not_found"):
        super().__init__(status.HTTP_404_NOT_FOUND, code, message)


class ConflictError(AppError):
    def __init__(self, message: str, code: str = "conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(status.HTTP_409_CONFLICT, code, message, details)


class NameConflictError(ConflictError):
    def __init__(self, message: str = "An item with this name already exists in this folder."):
        super().__init__(message, code="name_conflict")


class RootFolderProtectedError(ConflictError):
    def __init__(self, message: str = "The root folder cannot be deleted or renamed."):
        super().__init__(message, code="root_folder_protected")


class PayloadTooLargeError(AppError):
    def __init__(self, message: str = "The uploaded file exceeds the maximum allowed size."):
        super().__init__(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "payload_too_large", message)


class QuotaExceededError(AppError):
    def __init__(self, message: str = "User storage quota exceeded."):
        super().__init__(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "quota_exceeded", message)


class UnsupportedMediaTypeError(AppError):
    def __init__(self, message: str = "File extension is not supported."):
        super().__init__(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "unsupported_type", message)


class InvalidFileError(AppError):
    def __init__(self, message: str = "Invalid, corrupted, or encrypted file.", details: Optional[Dict[str, Any]] = None):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_file", message, details)


class FolderTooDeepError(AppError):
    def __init__(self, message: str = "Folder hierarchy depth limit exceeded."):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, "folder_too_deep", message)


class RateLimitedError(AppError):
    def __init__(self, message: str = "Rate limit exceeded.", retry_after: int = 60):
        super().__init__(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "rate_limited",
            message,
            headers={"Retry-After": str(retry_after)},
        )


def error_response_content(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    content = error_response_content(exc.code, exc.message, exc.details)
    headers = exc.headers or {}
    # Ensure X-Request-ID is preserved
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id
    headers["X-Content-Type-Options"] = "nosniff"
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Format details from pydantic errors
    errors = exc.errors()
    details = {"errors": errors}
    message = "Request validation failed."
    if errors:
        message = errors[0].get("msg", message)
    content = error_response_content("validation_error", message, details)
    headers = {"X-Content-Type-Options": "nosniff"}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=content, headers=headers)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    content = error_response_content("internal_error", "An internal server error occurred.")
    headers = {"X-Content-Type-Options": "nosniff"}
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["X-Request-ID"] = request_id
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=content, headers=headers)
