# Changelog

All notable changes to the UP Vidhan Sabha Election Ontology Engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] — 2026-05-26

### Added
- **Database Connection Pooling:** Integrated PgBouncer running in transaction pooling mode (`port 6432`) to scale concurrent database connections.
- **Observability Stack:** Configured Prometheus metrics exporter on FastAPI (`/metrics`) and deployed Grafana with automated provisioning settings and dashboards.
- **Distributed Task Locking:** Implemented atomic Redis-based locks (`SETNX`) inside the scraper pipeline (`pipeline/ingest/news_scraper.py`) to prevent duplicate, concurrent scraper executions.
- **Asynchronous DB Migration:** Upgraded the core database execution layer to use `postgresql+asyncpg` for non-blocking I/O operations.
- **Edge Caching:** Enabled Next.js Incremental Static Regeneration (ISR) with a 3600-second revalidation interval on booth lists (`/booths`) and booth detail panels (`/booths/[id]`) to minimize database roundtrips.

### Changed
- **Celery Worker Configuration:** Optimized Celery worker concurrency parameters (`concurrency=4`, `prefetch_multiplier=1`, `max_tasks_per_child=50`) to limit memory overhead and prevent database connection exhaustion.
- **Kubernetes Environment:** Updated `backend-deployment.yaml` manifests to dynamically construct connection strings referencing the PgBouncer cluster service.

### Fixed
- **Alembic Database Connection:** Ensured that Alembic migrations run directly against PostgreSQL (`port 5432`) since DDL queries are incompatible with PgBouncer transaction pooling.

---

## [1.1.0] — 2026-05-25

### Added
- **Unified Pipeline Module:** Grouped all data ingestion scrapers, ETL operations, graph loaders, and scheduled aggregation flows under a single, cohesive `pipeline/` package.
- **Backend Refactoring:** Renamed the legacy `api/` folder to `backend/` and adjusted backend module imports repository-wide to support namespace consistency.
- **Standardized Docker Configurations:** Consolidated separate development Dockerfiles into a dedicated `docker/` sub-directory (`docker/Dockerfile.backend`, `docker/Dockerfile.scraper`, etc.).

### Removed
- **Legacy Artifacts:** Deleted obsolete root-level files (`Dockerfile.api`, `Dockerfile.scraper`, `Dockerfile.dashboard`) to maintain a clean codebase.

---

## [1.0.0] — 2026-05-19

### Added
- **Core Relational DB Schema:** Created the initial schema migrations defining candidate facts, booth lists, electoral demographics, and sentiment feeds.
- **Neo4j Intelligence Graph:** Formulated loaders, schemas, and Cypher constraints establishing a 5-layer intelligence graph (booths, candidates, parties, local issues, and scheme gaps).
- **Multilingual NLP Engine:** Built a processing pipeline integrating Bhashini translation (Bhojpuri/Hindi) and Groq-based Llama models for automated political sentiment extraction.
- **Interactive Dashboards:** Created the initial user interfaces, including a Leaflet geospatial heatmap and a D3 knowledge graph explorer.
