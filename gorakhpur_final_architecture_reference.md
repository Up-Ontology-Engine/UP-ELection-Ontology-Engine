# Gorakhpur Election Intelligence Platform: The Master Reference Document

> **Mission:** Win Elections Through Hyper-Local Intelligence.
> This document serves as the single source of truth for the UP-Election-Ontology-Engine, synthesizing the architecture, ontology, ingestion pipeline, team distribution, and execution sprints.

---

## Part 1: Architecture & Capabilities

### 1.1 What the Engine Does
The engine maps the complete election geography of Gorakhpur Urban and builds a living, privacy-safe Knowledge Graph using Neo4j. By continuously ingesting digital signals (YouTube, News) through a multilingual NLP pipeline (Hindi/Bhojpuri), it computes real-time, booth-level "pulse scores". This enables hyper-local voter segmentation, allowing the campaign to know exactly *what* is being said, *where*, and *by whom*.

### 1.2 System Architecture Overview
```text
┌──────────────────────────────────────────────────────────────────────┐
│  L1: DATA COLLECTION (Ingestion Layer)                               │
│  ECI Booths │ Candidate Affidavits │ ECI Results │ eGramSwaraj       │
│  YouTube Influencers │ Jagran/Amar Ujala │ Field Surveys             │
└──────────────────────────────────────────────────────────────────────┘
                              │  (ingest_all.py via ingestion_config.json)
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  L2 & L3: NLP PIPELINE & BEHAVIORAL EXTRACTION (Postgres)            │
│  langdetect → Bhashini Translation → Groq (llama-3-70b) + Instructor │
│  Extracts: Emotion, Intensity, Entity Confidence, User Segmentation  │
└──────────────────────────────────────────────────────────────────────┘
                              │  (Entity Resolution & Geo-Alias Mapping)
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  L4: NEO4J KNOWLEDGE GRAPH (Ontology Layer)                          │
│  State→District→AC→Booth→Candidate→Party→Issue→PulseEvent→Scheme     │
│  Includes Intelligence Nodes: DataQuality, Narrative, Contradiction  │
└──────────────────────────────────────────────────────────────────────┘
                              │  (FastAPI + Analytics)
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  L7: DECISION INTELLIGENCE (Streamlit Dashboard)                     │
│  Outputs: Risk Scores, Opportunity Scores, Trend Stability           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: The Ontology & Schema

### 2.1 Core Neo4j Nodes
*   `State`, `District`, `AssemblyConstituency`, `Booth`, `Panchayat` (Geography)
*   `Candidate`, `Party`, `Election` (Political Entities)
*   `Issue`, `Scheme` (Topics)
*   `Influencer`, `PulseEvent`, `PoliticalEvent` (Signals & Causality)
*   `UserSegment` (Demographics: youth, women, farmer)

### 2.2 Intelligence Nodes
*   **`DataQuality`:** Tracks source bias and NLP confidence per booth.
*   **`SchemeGap`:** Categorizes governance failures (execution_gap, reach_gap).
*   **`ContradictionFlag`:** Flags diverging sentiments (e.g., YT says positive, News says negative).
*   **`Narrative`:** Detects macro trends (anti-incumbency, swing possible).

---

## Part 3: The Truth-Aware Ingestion Pipeline

The ingestion layer uses a centralized `ingestion_config.json` to manage all sources. It prevents the engine from being skewed by political IT cells or national noise.

### 3.1 Advanced Behavioral & Causal Processing
1.  **Comment-Level Geo-Filtering:** Videos from national influencers (like Dhruv Rathee or Sham Sharma) are heavily filtered. Only comments containing specific UP/Gorakhpur aliases are processed.
2.  **Virality & Engagement Tracking:** The system captures `likes`, `shares`, and `velocity`.
3.  **Deep LLM Extraction:** The Groq LLM extracts `emotion_type` (anger, hope), `intensity_score`, and infers the `segment_type`.
4.  **Bot Suppression & Deduplication:** MD5 hashing prevents duplicate news counting. A `bot_suspicion_score` penalizes highly viral but suspicious comments.
5.  **Causal Linking:** Pulse events are linked to `(PoliticalEvent)` nodes to track why a baseline shifted.

### 3.2 The Elite Reality-Weight Formula
Every event processed into Neo4j receives a mathematical impact weight:
```text
event_weight = 
  source_type_weight           // (survey:1.0, news:0.8, yt:0.6)
  × credibility_score          // (from config)
  × (1 - |bias_score|)         // (penalty for highly biased sources)
  × geo_confidence             // (booth > panchayat > AC)
  × entity_confidence          // (ambiguity penalty)
  × intensity_score            // (emotion intensity)
  × log(1 + engagement_likes)  // (virality multiplier)
  × (1 - bot_suspicion_score)  // (NOISE/BOT SUPPRESSION)
  × e^(-days_old / decay)      // (freshness time-decay)
```

---

## Part 4: Team Work Distribution (15 Person Team)

| Pod | Members | Responsibilities |
|-----|---------|------------------|
| **Infra & Backbone** | P2, P3, P15 | PostgreSQL, Neo4j, Docker infra. Official ECI/MyNeta scrapers. Security & Compliance (RPA 1951, PII hashing). |
| **Dynamic Signals** | P4, P5, P13 | Config-driven ingestion for YouTube, Jagran, Amar Ujala. Maintaining the `gorakhpur_aliases` and `political_lexicon`. |
| **NLP & Sentiment** | P6, P7, P8, P14 | Bhashini translation pipeline. Groq LLM Extraction. Multi-level geo-resolution (Booth→AC). |
| **Graph Analytics** | P9, P11 | Neo4j Cypher loaders. Cypher query library. Computing `risk_score` and `trend_stability_score`. |
| **UI, API, & PM** | P1, P10, P12 | Overall architecture orchestration. FastAPI endpoints. Streamlit Booth Analyst Console. |

---

## Part 5: The 5-Day Sprint Execution Plan

To prevent "analysis paralysis" and prove the architecture works, the team will execute a vertical slice targeting a single booth (Booth 223).

*   **Day 1 (Backbone & Schema):** Spin up Docker (Postgres/Neo4j). Lock the `ingestion_config.json` and the Neo4j schema. Setup the `.env` with Groq, YouTube, and Bhashini API keys.
*   **Day 2 (Data Ingestion):** Run the official ECI/MyNeta scrapers. Fetch the latest 50 videos from Gorakhpur News and Sham Sharma. Execute the comment-level geo-filtering.
*   **Day 3 (NLP Pipeline):** Push the raw comments through Bhashini translation. Use Groq to extract JSON structures containing emotion, intensity, and location mentions. Map mentions to Booth 223.
*   **Day 4 (Graph Loading & Analytics):** Seed the Neo4j database. Calculate the `event_weight` for all PulseEvents. Compute the `risk_score` for Booth 223 based on the aggregated data.
*   **Day 5 (Dashboard & Validation):** Expose the data via FastAPI. Build the Streamlit Booth 223 dashboard card. **Run the Validation Loop:** Manually review the output against ground truth to calibrate the `bot_suspicion_score` and bias weights.

---

## Part 6: Success Metrics & Roadmap

*   **Metric 1:** NLP extraction confidence > 85%.
*   **Metric 2:** Daily data freshness for the dashboard.
*   **Metric 3:** Pre-election booth sentiment vs actual results correlation > 0.75.

**Roadmap:**
1.  **Phase 1:** Gorakhpur Urban AC (1 AC, ~300 booths) — *Current Focus*
2.  **Phase 2:** Campierganj AC (2nd AC)
3.  **Phase 3:** Full Gorakhpur District
4.  **Phase 4:** Real-time WhatsApp/SMS campaign delivery integration
