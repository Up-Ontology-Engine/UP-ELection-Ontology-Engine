"""FastAPI application — Gorakhpur KG dashboard API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# ── Structured logging — configure before any other imports ───────────────────
from .logging_config import configure_logging, get_logger

configure_logging(service="api")
_log = get_logger(__name__)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ruff: noqa: E402
from .db import get_async_pg_engine
from .queries import init_beneficiary_tables, init_chat_tables
from .routers import ac, booths, graph, health, reasoning
from .validation import InputValidationRoute

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup warmup → yield → shutdown cleanup."""
    _log.info("API startup", extra={"version": "0.1.0"})

    # ── Init sync tables (chat, beneficiary) ──────────────────────────────
    try:
        init_chat_tables()
    except Exception as exc:
        _log.error("Chat tables init failed", extra={"error": str(exc)})
    try:
        init_beneficiary_tables()
    except Exception as exc:
        _log.error("Beneficiary tables init failed", extra={"error": str(exc)})

    # ── Warm up the async PostgreSQL connection pool ───────────────────────
    try:
        engine = get_async_pg_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
        _log.info("Async PG pool warmed up")
    except Exception as exc:
        _log.warning("Async PG pool warmup failed (non-fatal): %s", exc)

    yield  # ── Application runs here ────────────────────────────────────────

    # ── Graceful shutdown ─────────────────────────────────────────────────
    try:
        await get_async_pg_engine().dispose()
        _log.info("Async PG pool disposed")
    except Exception:
        pass


app = FastAPI(
    title="Gorakhpur KG API",
    description="Booth-level political intelligence for Gorakhpur Urban AC",
    version="0.1.0",
    lifespan=lifespan,
)
app.router.route_class = InputValidationRoute
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus metrics middleware + /metrics endpoint ─────────────────────────
try:
    from .metrics import metrics_endpoint, setup_metrics

    setup_metrics(app)
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)
except Exception as _metrics_err:
    _log.warning("Metrics setup failed (prometheus_client not installed?): %s", _metrics_err)

# ── Include Domain Routers ────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(ac.router)
app.include_router(booths.router)
app.include_router(graph.router)
app.include_router(reasoning.router)
