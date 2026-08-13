"""
Two lightweight ASGI middlewares:

1. RequestSizeLimitMiddleware — rejects oversized request bodies before
   they're read into memory or reach Pydantic validation, using
   Content-Length as a cheap first gate.

2. SecurityHeadersMiddleware — adds standard defensive headers to every
   response. These don't replace real security controls (auth, Firestore
   ownership checks) but are cheap, expected hardening for a public API.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config.settings import get_settings


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        content_length = request.headers.get("content-length")

        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = None

            if length is not None and length > settings.max_request_body_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Your message is too long."},
                )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response
