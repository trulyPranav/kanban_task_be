import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.config import settings
from core.database import init_db
from core.rate_limiter import limiter
from routers import comments_router, tasks_router, users_router

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    logger.info("Starting up — initialising database …")
    await init_db()
    logger.info("Application ready.")
    yield
    logger.info("Shutting down.")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "Production-ready Kanban Task Management API. "
        "Supports tasks, comments and users with full pagination, "
        "filtering and per-route rate limiting."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ─── Rate limiter ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Security headers middleware ──────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects OWASP-recommended security headers on every response.
    Adjust Content-Security-Policy to match your actual frontend origin.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        response: Response = await call_next(request)
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Block clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Force HTTPS when deployed behind TLS termination
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        # Restrict referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Disable browser features not needed by this API
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Basic CSP — tighten for your deployment
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        # Remove server fingerprinting header
        response.headers.pop("Server", None)
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ─── Request-ID middleware ────────────────────────────────────────────────────
class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Echoes (or generates) an X-Request-ID on every response.
    Clients can send their own X-Request-ID for end-to-end tracing;
    if absent a new UUID-4 is created.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)


# ─── Global error handler ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s", request.method, request.url, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────
PREFIX = settings.API_V1_PREFIX
app.include_router(users_router, prefix=PREFIX)
app.include_router(tasks_router, prefix=PREFIX)
app.include_router(comments_router, prefix=PREFIX)


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Health check")
async def health() -> dict:
    return {"status": "healthy", "version": "1.0.0"}
