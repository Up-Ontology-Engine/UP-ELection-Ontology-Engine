# Local Setup Guide

## Prerequisites
- Python 3.11+
- Docker Desktop (for Postgres + Neo4j + Redis)
- Git

## Step 1 — Clone & install

```bash
git clone git@github.com:Aryan-en/UP-ELection-Ontology-Engine.git
cd UP-ELection-Ontology-Engine
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Step 2 — Configure environment

```bash
cp .env.example .env
# Edit .env and fill in:
#   GROQ_API_KEY        — from console.groq.com (free)
#   BHASHINI_API_KEY    — from bhashini.gov.in (free, may take 24h approval)
#   BHASHINI_USER_ID
#   NEO4J_PASSWORD=gorakhpur_neo4j_pass  (matches docker-compose.yml)
```

## Step 3 — Start infrastructure

```bash
docker-compose up -d
# Wait ~30s for Neo4j to fully start
docker-compose ps    # all should be healthy
```

## Step 4 — Initialize databases

```bash
# PostgreSQL schema (using Alembic)
alembic upgrade head

# Seed initial issues list
psql postgresql://postgres:postgres@localhost:5432/gorakhpur_db \
     -f data/seeds/seed_issues.sql

# Neo4j constraints (Neo4j browser at http://localhost:7474)
# User: neo4j  Password: gorakhpur_neo4j_pass
# Paste contents of pipeline/graph/constraints.cypher and run
```

## Step 5 — Run ingestion

```bash
# Day 1: official structure
python -m pipeline.ingest.eci_booths
python -m pipeline.ingest.myneta_candidates

# Day 2: digital signals
python -m pipeline.ingest.youtube_comments
python -m pipeline.ingest.news_scraper
```

## Step 6 — Run NLP pipeline

```bash
# Stage raw → pulse_events_raw
python -m pipeline.etl.pulse_event_prep

# Run NLP (requires GROQ_API_KEY)
python -m pipeline.flows.nlp.flow_sentiment
```

## Step 7 — Compute metrics

```bash
python -m pipeline.analytics.booth_metrics
```

## Step 8 — Start API + Dashboard

```bash
# Terminal 1 — API
uvicorn backend.main:app --reload --port 8000
# Check: http://localhost:8000/docs

# Terminal 2 — Next.js Dashboard
cd frontend/nextjs
npm install
npm run dev
# Opens: http://localhost:3000
```

## Troubleshooting

**Neo4j won't start:**
```bash
docker logs gorakhpur_neo4j
# Common fix: increase Docker memory to 4GB+
```

**Bhashini API returns 401:**
```bash
# Check BHASHINI_USER_ID and BHASHINI_API_KEY in .env
# Registration: https://bhashini.gov.in/ulca/auth/register
```

**Dashboard shows "Could not load booths":**
```bash
# Ensure API is running: uvicorn backend.main:app --reload
# Ensure booth_master has data: python -m pipeline.ingest.eci_booths
```

**Groq rate limit:**
```bash
# Reduce batch size: edit NLP_BATCH_SIZE=20 in .env
# Or add time.sleep(1) in pipeline/nlp/extractor.py between calls
```

## Production Configuration & Tuning

### 1. Database Connection Pooling (PgBouncer)
To protect PostgreSQL under high concurrent load, PgBouncer is deployed on port `6432` in **Transaction Pooling** mode. 
- **Application Services (FastAPI, Celery workers):** Must connect to PgBouncer (`port 6432`). Database URLs should use `postgresql://...:6432/...`.
- **Database Migrations (Alembic / DDL):** Must connect directly to PostgreSQL (`port 5432`) since transaction pooling is incompatible with complex schema migrations.

### 2. Distributed Task Locking
To prevent duplicate scraper runs if a task takes longer than its scheduled execution interval, scrapers use a Redis-based distributed lock:
- Scrapers perform `redis.set(lock_key, "locked", nx=True, ex=3600)` at startup.
- If the lock exists, the task exits gracefully to avoid duplicate database operations.

### 3. Celery Performance Tuning
Celery workers are tuned for stable resource and database connection management:
- `worker_concurrency = 4` (limits concurrent task runs per worker)
- `worker_prefetch_multiplier = 1` (disables pre-fetching to prevent message starvation)
- `worker_max_tasks_per_child = 50` (periodically recycles processes to eliminate Python memory leaks)

### 4. Observability Stack
Production telemetry is fully integrated:
- **FastAPI Prometheus Metrics:** Exposed on `/metrics` via `prometheus-fastapi-instrumentator`.
- **Grafana Dashboard:** Access at `http://localhost:3000` (admin/admin). Custom dashboards visualize real-time request volume, latency distribution, Redis cache hit/miss ratio, and PgBouncer connection pool sizes.
