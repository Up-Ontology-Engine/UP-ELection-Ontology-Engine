"""
Prometheus metrics endpoint for the Gorakhpur Election Ontology Engine API.

Exposes /metrics (plain text Prometheus format) for scraping by:
  - Prometheus + Grafana stack
  - AWS CloudWatch Agent (Prometheus scrape mode)
  - Any OpenMetrics-compatible collector

Metrics exposed:
  api_requests_total{method, endpoint, status}    — counter
  api_request_latency_seconds{method, endpoint}   — histogram
  api_cache_hits_total / api_cache_misses_total   — counters
  neo4j_query_latency_seconds{query_type}         — histogram
  nlp_extraction_total{status}                    — counter
  scraper_articles_ingested_total{source}         — counter
  db_pool_checked_out                             — gauge (SQLAlchemy pool)

Usage in main.py:
    from backend.metrics import setup_metrics, metrics_endpoint
    setup_metrics(app)
    app.add_route("/metrics", metrics_endpoint)

Or standalone:
    python -m api.metrics   # starts a simple HTTP server on :9090
"""
from __future__ import annotations

import time
import os
from typing import Callable

# ── Prometheus client — optional dependency ───────────────────────────────────
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, CollectorRegistry,
        generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    )
    _PROM_AVAILABLE = True
except ImportError:
    _PROM_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)


# ── Metric definitions ─────────────────────────────────────────────────────────

if _PROM_AVAILABLE:
    REQUEST_COUNT = Counter(
        "api_requests_total",
        "Total API requests",
        ["method", "endpoint", "status"],
    )

    REQUEST_LATENCY = Histogram(
        "api_request_latency_seconds",
        "API request latency in seconds",
        ["method", "endpoint"],
        buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    CACHE_HITS = Counter(
        "api_cache_hits_total",
        "Redis cache hit count",
        ["endpoint"],
    )

    CACHE_MISSES = Counter(
        "api_cache_misses_total",
        "Redis cache miss count",
        ["endpoint"],
    )

    NEO4J_LATENCY = Histogram(
        "neo4j_query_latency_seconds",
        "Neo4j query execution latency",
        ["query_type"],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 3.0, 10.0],
    )

    NLP_TOTAL = Counter(
        "nlp_extraction_total",
        "LLM NLP extraction calls",
        ["status"],   # success | error | skipped
    )

    SCRAPER_ARTICLES = Counter(
        "scraper_articles_ingested_total",
        "Articles ingested by scraper",
        ["source"],
    )

    DB_POOL_CHECKED_OUT = Gauge(
        "db_pool_checked_out",
        "SQLAlchemy connection pool — connections currently checked out",
    )


# ── Instrumentation helpers ───────────────────────────────────────────────────

def record_request(method: str, endpoint: str, status: int, latency: float) -> None:
    """Record a completed API request. Call from middleware."""
    if not _PROM_AVAILABLE:
        return
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)


def record_cache_hit(endpoint: str) -> None:
    if _PROM_AVAILABLE:
        CACHE_HITS.labels(endpoint=endpoint).inc()


def record_cache_miss(endpoint: str) -> None:
    if _PROM_AVAILABLE:
        CACHE_MISSES.labels(endpoint=endpoint).inc()


def record_neo4j_query(query_type: str, latency: float) -> None:
    if _PROM_AVAILABLE:
        NEO4J_LATENCY.labels(query_type=query_type).observe(latency)


def record_nlp_extraction(status: str = "success") -> None:
    if _PROM_AVAILABLE:
        NLP_TOTAL.labels(status=status).inc()


def record_scraper_article(source: str) -> None:
    if _PROM_AVAILABLE:
        SCRAPER_ARTICLES.labels(source=source).inc()


def update_db_pool_gauge(checked_out: int) -> None:
    if _PROM_AVAILABLE:
        DB_POOL_CHECKED_OUT.set(checked_out)


# ── FastAPI middleware integration ─────────────────────────────────────────────

def setup_metrics(app) -> None:
    """
    Attach Prometheus metrics middleware to a FastAPI app.

    Call once at startup:
        setup_metrics(app)
    """
    if not _PROM_AVAILABLE:
        logger.warning("[metrics] prometheus_client not installed — /metrics endpoint disabled.")
        return

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    class PrometheusMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable):
            start = time.perf_counter()
            response = await call_next(request)
            latency = time.perf_counter() - start

            # Normalise endpoint path — remove dynamic segments for cardinality control
            path = request.url.path
            # Replace UUIDs and booth/AC IDs with placeholders
            import re
            path = re.sub(r"/[A-Z]{2,6}_[0-9]{3,4}", "/{ac_id}", path)
            path = re.sub(r"/[A-Z]{2,6}_B[0-9]{3,4}", "/{booth_id}", path)
            path = re.sub(r"/\d+", "/{id}", path)

            record_request(
                method=request.method,
                endpoint=path,
                status=response.status_code,
                latency=latency,
            )
            return response

    app.add_middleware(PrometheusMiddleware)
    logger.info("[metrics] Prometheus middleware attached.")


async def metrics_endpoint(request=None, response=None):
    """
    FastAPI/Starlette route handler for GET /metrics.
    Returns Prometheus text format.
    """
    if not _PROM_AVAILABLE:
        from starlette.responses import PlainTextResponse
        return PlainTextResponse("# prometheus_client not installed\n", status_code=503)

    from starlette.responses import Response as StarletteResponse
    data = generate_latest(REGISTRY)
    return StarletteResponse(content=data, media_type=CONTENT_TYPE_LATEST)


# ── Standalone test server ─────────────────────────────────────────────────────

if __name__ == "__main__":
    if not _PROM_AVAILABLE:
        print("Install prometheus_client: pip install prometheus-client")
        raise SystemExit(1)

    import http.server
    import threading

    PORT = int(os.environ.get("METRICS_PORT", "9090"))

    class MetricsHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/metrics":
                data = generate_latest(REGISTRY)
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE_LATEST)
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, *args): pass  # suppress HTTP logs

    server = http.server.HTTPServer(("0.0.0.0", PORT), MetricsHandler)
    print(f"[metrics] Serving on http://0.0.0.0:{PORT}/metrics")
    server.serve_forever()
