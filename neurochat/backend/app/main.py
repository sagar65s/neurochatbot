"""
FastAPI application entrypoint. Wires up middleware, CORS, routes, and a
global exception handler that guarantees raw internal errors never leak
to the client.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, chat, conversations
from app.config.settings import get_settings
from app.firebase.admin import init_firebase_admin
from app.middleware.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(title="NeuroChat API", version="1.0.0")

settings = get_settings()

# Order matters: middlewares run outside-in on the way in, inside-out on
# the way out. Security headers and size limit first, then CORS closest
# to the route.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(conversations.router)


@app.on_event("startup")
async def on_startup():
    init_firebase_admin()
    logger.info("NeuroChat API started.")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )
