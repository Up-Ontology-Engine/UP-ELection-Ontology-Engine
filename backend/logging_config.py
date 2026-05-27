"""
Structured logging configuration for the Gorakhpur Election Ontology Engine.

Provides JSON-formatted log output in production and human-readable output
in development.  Every log record is enriched with:
  - request_id  (per-request UUID, injected by middleware)
  - booth_id    (when processing booth-specific data)
  - ac_id       (assembly constituency context)
  - service     (api | scraper | nlp | graph)

Usage:
    from backend.logging_config import get_logger, configure_logging

    configure_logging()  # call once at startup
    logger = get_logger(__name__)
    logger.info("Processing booth", extra={"booth_id": "GKP_B001", "event": "nlp.extract"})
"""

from __future__ import annotations

import logging
import logging.config
import os
import sys
import uuid
from typing import Any

# ── Contextvars for per-request enrichment ────────────────────────────────────
try:
    from contextvars import ContextVar

    _request_id_var: ContextVar[str] = ContextVar("request_id", default="")
    _booth_id_var: ContextVar[str] = ContextVar("booth_id", default="")
    _ac_id_var: ContextVar[str] = ContextVar("ac_id", default="")
    _CONTEXTVARS_OK = True
except ImportError:
    _CONTEXTVARS_OK = False


def set_request_context(
    request_id: str | None = None,
    booth_id: str = "",
    ac_id: str = "",
) -> str:
    """Set per-request context variables. Returns the request_id used."""
    rid = request_id or str(uuid.uuid4())[:8]
    if _CONTEXTVARS_OK:
        _request_id_var.set(rid)
        _booth_id_var.set(booth_id)
        _ac_id_var.set(ac_id)
    return rid


def get_request_id() -> str:
    if _CONTEXTVARS_OK:
        return _request_id_var.get()
    return ""


# ── JSON Formatter ────────────────────────────────────────────────────────────


class JsonFormatter(logging.Formatter):
    """
    Emits each log record as a single-line JSON object.
    Fields: timestamp, level, logger, message, + any extras.
    """

    _SERVICE = os.environ.get("SERVICE_NAME", "api")

    def format(self, record: logging.LogRecord) -> str:
        import json
        import traceback

        base: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "service": self._SERVICE,
            "msg": record.getMessage(),
        }

        # Request context enrichment
        if _CONTEXTVARS_OK:
            if rid := _request_id_var.get():
                base["request_id"] = rid
            if bid := _booth_id_var.get():
                base["booth_id"] = bid
            if aid := _ac_id_var.get():
                base["ac_id"] = aid

        # Extra fields attached via logger.info("msg", extra={...})
        skip = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "taskName",
        }
        for k, v in record.__dict__.items():
            if k not in skip and not k.startswith("_"):
                base[k] = v

        if record.exc_info:
            base["exc"] = traceback.format_exception(*record.exc_info)[-1].strip()

        return json.dumps(base, ensure_ascii=False, default=str)


# ── Human-readable formatter (dev) ────────────────────────────────────────────


class DevFormatter(logging.Formatter):
    _COLORS = {
        "DEBUG": "\033[36m",  # cyan
        "INFO": "\033[32m",  # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",  # red
        "CRITICAL": "\033[35m",  # magenta
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self._COLORS.get(record.levelname, "")
        ts = self.formatTime(record, "%H:%M:%S")
        rid = _request_id_var.get() if _CONTEXTVARS_OK else ""
        rid_tag = f"[{rid}] " if rid else ""
        prefix = f"{color}{record.levelname:<8}{self._RESET} {ts} {rid_tag}{record.name}"
        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        return f"{prefix}: {msg}"


# ── Main configure function ───────────────────────────────────────────────────


def configure_logging(
    level: str | None = None,
    json_output: bool | None = None,
    service: str = "api",
) -> None:
    """
    Configure root logging.

    Args:
        level:       Override log level. Reads LOG_LEVEL env var, defaults to INFO.
        json_output: Use JSON formatter. Reads LOG_FORMAT=json env var.
                     Auto-detects: True in production (non-TTY), False in dev (TTY).
        service:     Service name tag emitted in every JSON record.
    """
    os.environ["SERVICE_NAME"] = service

    _level = level or os.environ.get("LOG_LEVEL", "INFO").upper()

    _json = json_output
    if _json is None:
        env_fmt = os.environ.get("LOG_FORMAT", "").lower()
        if env_fmt == "json":
            _json = True
        elif env_fmt == "text":
            _json = False
        else:
            _json = not sys.stdout.isatty()  # JSON in prod (non-TTY), text in dev

    formatter = JsonFormatter() if _json else DevFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(_level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("urllib3", "httpx", "httpcore", "neo4j", "botocore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging configured",
        extra={"level": _level, "format": "json" if _json else "text", "service": service},
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. configure_logging() must be called first."""
    return logging.getLogger(name)
