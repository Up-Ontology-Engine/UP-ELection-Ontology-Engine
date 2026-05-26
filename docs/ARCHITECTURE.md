# Architecture and System Design

This document details the system design, database integration models, data flow pipelines, and intelligence layering architecture of the UP Vidhan Sabha Election Ontology Engine.

---

## Architectural Philosophy

The platform is designed around a **hybrid data topology** that leverages both relational and graph database models. 
- **Relational Databases (PostgreSQL):** Used for structured facts, demographics, transaction tracking, and tabular records (e.g., voter turnout tables, target lists, chat session histories) that require strict schema enforcement and acid transactional safety.
- **Graph Databases (Neo4j):** Used to represent complex, highly connected semantic entities (booths, candidates, parties, local issues, and government schemes) where relationship traversals (such as calculating the influence of sentiment anomalies across booths) are performance-critical.

---

## Data Integration & Component Layout

```
                  ┌───────────────────────────────┐
                  │      Next.js Frontend         │
                  │   (Cached via Next.js ISR)   │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │       FastAPI API Backend     │
                  │      (Instrumented Metrics)   │
                  └──────┬──────────────┬─────────┘
                         │              │
        (Transaction     │              │ (Graph
         Connections)    │              │  Connections)
                         ▼              ▼
                  ┌────────────┐  ┌───────────┐
                  │ PgBouncer  │  │   Neo4j   │
                  │  (Pooler)  │  │ (Graph DB)│
                  └──────┬─────┘  └─────▲─────┘
                         │              │
                         ▼              │ (Sync / Ingestion Loaders)
                  ┌────────────┐        │
                  │ PostgreSQL │────────┘
                  │ (Fact DB)  │
                  └────────────┘
                         ▲
                         │
                         ▼
                  ┌────────────┐
                  │   Redis    │◄──────── Celery Beat Scheduler
                  │ (Lock/Queue)│
                  └────────────┘
                         ▲
                         │ (Task Executions)
                  ┌──────┴─────┐
                  │   Celery   │
                  │   Worker   │
                  └────────────┘
```

---

## Data Ingestion & Extraction Pipeline

The data ingestion pipeline imports unstructured and structured sources into PostgreSQL before performing multilingual translations and LLM sentiment extracts to build graph node relationships.

### 1. Ingestion Flow (Unstructured & Structured Data)
1.  **ECI & MyNeta Ingest:** Booth mappings and ADR candidate documents are imported as tables inside PostgreSQL.
2.  **Digital Signal Gathering:** Periodic scrapers extract local news articles and YouTube political commentary, caching raw data in the relational database.
3.  **Bhashini Translation Loop:** Unstructured text comments (frequently written in a mix of Bhojpuri and Hindi) are sent to the Bhashini API, returning clean Hindi translations.
4.  **Groq NLP Classification:** Translated text is processed using Llama 3.3 70B models constrained by Pydantic schemas to yield structured JSON components:
    *   Entity mentions (parties, candidates, local issues).
    *   Sentiment polarity (scale from -1.0 to 1.0) and confidence.
5.  **Geo-Resolution:** Location mentions are mapped to exact booth parts using fuzzy string matching.

---

## The 5-Layer Intelligence Graph

The processed PostgreSQL events are compiled into Neo4j nodes and mapped across five intelligence layers:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. NARRATIVE LAYER (anti_incumbency, development, price_rise)          │
└────────────────────────────────────▲────────────────────────────────────┘
                                     │
┌────────────────────────────────────┴────────────────────────────────────┐
│ 4. CONTRADICTION LAYER (YouTube vs. local news sentiment divergence)    │
└────────────────────────────────────▲────────────────────────────────────┘
                                     │
┌────────────────────────────────────┴────────────────────────────────────┐
│ 3. ALIAS EXPANSION LAYER (locality fuzzy matching to booth IDs)        │
└────────────────────────────────────▲────────────────────────────────────┘
                                     │
┌────────────────────────────────────┴────────────────────────────────────┐
│ 2. SCHEME GAP LAYER (execution, reach, and awareness gaps in schemes)   │
└────────────────────────────────────▲────────────────────────────────────┘
                                     │
┌────────────────────────────────────┴────────────────────────────────────┐
│ 1. DATA QUALITY LAYER (survey volume, geo resolution accuracy score)    │
└─────────────────────────────────────────────────────────────────────────┘
```

1.  **Data Quality Layer:** Evaluates input bias, geolocation availability, and NLP extraction confidence levels to assign an overall reliability score per booth.
2.  **Scheme Gap Layer:** Cross-references scheme completion facts against localized sentiment data to classify target areas (e.g., identifying high beneficiary counts with negative sentiment as an `execution_gap`).
3.  **Alias Expansion Layer:** Learns local locality aliases dynamically from geo-resolver failures, expanding search dictionaries.
4.  **Contradiction Layer:** Monitors divergence metrics between public commentary (YouTube Comments) and regional publications (News Scrapes) to identify swings.
5.  **Narrative Layer:** Aggregates sentiment data over time to extract dominant local sentiments (e.g., ruling party negative scoring across multiple issues signals `anti_incumbency`).

---

## AI Reasoning Pipeline

The interactive reasoning engine processes natural language questions into structured graph queries:

1.  **User Input:** The analyst submits a query (e.g., *"Which booths in Gorakhpur show negative sentiment on water schemes?"*).
2.  **Cypher Translation:** The FastAPI server sends the graph schema structure along with the prompt to the LLM to generate an optimized Cypher query.
3.  **Dual Retrieval:**
    *   **Graph Query:** Runs the generated Cypher query directly in Neo4j.
    *   **Web Search:** Executes parallel fallback queries in DuckDuckGo/Wikipedia to enrich historical facts.
4.  **Synthesis:** The primary Sarvam AI model (or fallback Gemini endpoint) compiles the graph records and search results to produce a unified, natural language analysis.
5.  **Persistence:** The session, query, and synthesized answer are committed to database audit logs.

---

## Caching & Concurrency Controls

-   **Next.js ISR:** Pages `/booths` and `/booths/[id]` are pre-rendered at build time. Reads are served from static memory, refreshing in the background once per hour. This completely isolates PostgreSQL/Neo4j from direct read overhead.
-   **PgBouncer Pool:** The backend leverages connection pooling to prevent FastAPI and Celery workers from exhausting PostgreSQL sockets under sudden request load.
-   **Redis Locks:** Prevents Celery tasks from executing concurrently, ensuring that only a single instance of any news scraper or analytics runner holds write locks.
