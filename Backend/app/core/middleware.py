import json
from uuid import uuid4
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.errors import error_response_content
from app.core.logging import request_id_ctx


class RequestIdAndSecurityHeadersMiddleware:
    """
    Middleware that:
    1. Extracts or assigns an X-Request-ID.
    2. Stores it in request context and logging context.
    3. Adds X-Request-ID and X-Content-Type-Options: nosniff to all responses.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Find incoming X-Request-ID
        headers = dict(scope.get("headers", []))
        req_id = headers.get(b"x-request-id", b"").decode("latin1").strip()
        if not req_id:
            req_id = str(uuid4())

        # Set into ContextVar for logging
        token = request_id_ctx.set(req_id)
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = req_id

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                msg_headers = list(message.get("headers", []))
                # Add X-Request-ID
                msg_headers.append((b"x-request-id", req_id.encode("latin1")))
                # Add X-Content-Type-Options
                msg_headers.append((b"x-content-type-options", b"nosniff"))
                message["headers"] = msg_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            request_id_ctx.reset(token)


class UploadSizeLimitMiddleware:
    """
    Pure ASGI middleware enforcing upload size limit early:
    1. Checks Content-Length header against (MAX_UPLOAD_MB + overhead).
    2. Wraps receive to count bytes for chunked uploads without Content-Length.
    """

    MULTIPART_OVERHEAD_BYTES = 64 * 1024  # 64 KB overhead for form fields/boundaries

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        path = scope.get("path", "")

        # Only apply on file upload endpoints
        if method == "POST" and (path == "/api/v1/files" or path.endswith("/files")):
            max_bytes = (settings.MAX_UPLOAD_MB * 1024 * 1024) + self.MULTIPART_OVERHEAD_BYTES
            headers = dict(scope.get("headers", []))
            content_length_header = headers.get(b"content-length")

            req_id = scope.get("state", {}).get("request_id", str(uuid4()))

            if content_length_header:
                try:
                    content_length = int(content_length_header.decode("latin1"))
                    if content_length > max_bytes:
                        await self._send_413_response(send, req_id)
                        return
                except ValueError:
                    pass

            # Wrap receive for streaming/chunked requests
            bytes_received = 0

            async def custom_receive() -> dict:
                nonlocal bytes_received
                message = await receive()
                if message["type"] == "http.request":
                    body = message.get("body", b"")
                    bytes_received += len(body)
                    if bytes_received > max_bytes:
                        # Exceeded limit during streaming
                        raise UploadTooLargeException()
                return message

            try:
                await self.app(scope, custom_receive, send)
            except UploadTooLargeException:
                await self._send_413_response(send, req_id)
            return

        await self.app(scope, receive, send)

    async def _send_413_response(self, send: Send, req_id: str) -> None:
        body = json.dumps(
            error_response_content(
                "payload_too_large",
                f"The upload exceeds the maximum allowed size of {settings.MAX_UPLOAD_MB}MB.",
            )
        ).encode("utf-8")

        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("latin1")),
            (b"x-request-id", req_id.encode("latin1")),
            (b"x-content-type-options", b"nosniff"),
        ]

        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": headers,
        })
        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False,
        })


class UploadTooLargeException(Exception):
    pass
