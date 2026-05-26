"""FastAPI application — Gorakhpur KG dashboard API."""
from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# ── Structured logging — configure before any other imports ───────────────────
from .logging_config import configure_logging, get_logger
configure_logging(service="api")
_log = get_logger(__name__)

from .queries import init_chat_tables, init_beneficiary_tables
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .validation import InputValidationRoute
from .cache import clear_api_cache
from .routers import ac, booths, graph, reasoning, health

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Gorakhpur KG API",
    description="Booth-level political intelligence for Gorakhpur Urban AC",
    version="0.1.0",
)
app.router.route_class = InputValidationRoute
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def _startup():
    _log.info("API startup", extra={"version": app.version})
    try:
        init_chat_tables()
    except Exception as exc:
        _log.error("Chat tables init failed", extra={"error": str(exc)})
    try:
        init_beneficiary_tables()
    except Exception as exc:
        _log.error("Beneficiary tables init failed", extra={"error": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus metrics middleware + /metrics endpoint ─────────────────────────
try:
    from .metrics import setup_metrics, metrics_endpoint
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
