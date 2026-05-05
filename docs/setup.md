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
# PostgreSQL schema
psql postgresql://postgres:postgres@localhost:5432/gorakhpur_db \
     -f db/migrations/001_initial.sql
psql postgresql://postgres:postgres@localhost:5432/gorakhpur_db \
     -f db/seeds/seed_issues.sql

# Neo4j constraints (Neo4j browser at http://localhost:7474)
# User: neo4j  Password: gorakhpur_neo4j_pass
# Paste contents of graph/constraints.cypher and run
```

## Step 5 — Run ingestion

```bash
# Day 1: official structure
python -m ingestion.eci_booths
python -m ingestion.myneta_candidates

# Day 2: digital signals
python -m ingestion.youtube_comments
python -m ingestion.news_scraper
```

## Step 6 — Run NLP pipeline

```bash
# Stage raw → pulse_events_raw
python -m etl.pulse_event_prep

# Run NLP (requires GROQ_API_KEY)
python -m flows.nlp.flow_sentiment
```

## Step 7 — Compute metrics

```bash
python -m analytics.booth_metrics
```

## Step 8 — Start API + Dashboard

```bash
# Terminal 1 — API
uvicorn api.main:app --reload --port 8000
# Check: http://localhost:8000/docs

# Terminal 2 — Dashboard
streamlit run dashboard/app.py
# Opens: http://localhost:8501
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
# Ensure API is running: uvicorn api.main:app --reload
# Ensure booth_master has data: python -m ingestion.eci_booths
```

**Groq rate limit:**
```bash
# Reduce batch size: edit NLP_BATCH_SIZE=20 in .env
# Or add time.sleep(1) in nlp/extractor.py between calls
```
