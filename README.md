# UP Election Ontology Engine — Gorakhpur Booth Knowledge Graph

**Mission: Win Elections Through Hyper-Local Intelligence**

A booth-level political intelligence platform for Gorakhpur Urban AC (UP Vidhan Sabha). Combines a Neo4j knowledge graph, a multilingual NLP pipeline, historical election data, and live digital signals to deliver analyst-grade insights down to individual polling booths.

> Gorakhpur Urban AC-322 · ~300 booths · Hindi / Bhojpuri / English · PostgreSQL + Neo4j + Next.js

---

## What This Builds

```
Booth 223 (Gorakhpur Urban)
├── Historical: BJP won last 2 elections | Vote share: 55% → 48% (declining)
├── Digital Lean: Lean BJP
├── Data Quality: MEDIUM — 78% YouTube | 28% AC-level mapping
├── Top Issues: Water +22%  |  Jobs +10%
├── Candidate Insights: BJP +ve on development, -ve on water
├── Scheme Gap: PMAY → reach_gap (low beneficiaries + complaints high)
├── Dominant Narrative: anti_incumbency (strength 0.62)
├── Mixed Signal: BJP — YouTube +0.4 vs News -0.3 (SWING_INDICATOR)
├── Key Insight: Strong base, growing dissatisfaction on water
└── Recommendation: Focus campaign on water + jobs
```

Every field is backed by real data: ECI booths, MyNeta affidavits, eGramSwaraj schemes, YouTube comments, local news — all flowing through a deterministic multilingual NLP pipeline into a Neo4j knowledge graph with 5 intelligence layers.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  DATA SOURCES                                                         │
│  ECI Booths │ MyNeta Affidavits │ ECI Results │ eGramSwaraj │ MGNREGA │
│  YouTube Comments │ Jagran/Amar Ujala News │ Field Surveys           │
└──────────────────────────────────────────────────────────────────────┘
                              │  ingestion/
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  POSTGRES (gorakhpur_db)                                              │
│  ac_master │ booth_master │ candidate_master │ booth_results         │
│  scheme_activity │ yt_comments │ news_articles │ pulse_events        │
│  ── Intelligence layer ──                                             │
│  data_quality_metrics │ booth_narratives                             │
│  contradiction_flags  │ scheme_gap_analysis                          │
│  ── Chat / Conversion ──                                             │
│  chat_sessions │ chat_messages │ scheme_beneficiaries                │
└──────────────────────────────────────────────────────────────────────┘
                              │  nlp/pipeline.py
                              │  lang_detect → bhashini → sarvam/gemini → geo_resolve
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NEO4J  — Full Property Graph                                         │
│  State→District→AC→Booth→Candidate→Party→Issue→PulseEvent→Scheme    │
│  ── Intelligence nodes ──                                             │
│  Booth→DataQuality │ Booth→Narrative→Issue/Party/Candidate          │
│  Booth→SchemeGap→Scheme/Issue │ Booth→ContradictionFlag→Party       │
└──────────────────────────────────────────────────────────────────────┘
                              │  analytics/ + graph/loaders/
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FASTAPI  (40+ endpoints)                                             │
│  Booths · Pulse · Issues · Quality · Narratives · Contradictions     │
│  Candidates · Schemes · Demographics · Graph · Heatmap · Reasoning   │
│  Conversion Engine · Chat Sessions · Digital Twin                    │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NEXT.JS FRONTEND  (10 pages)                                         │
│  Command Center · Booths · Heatmap · Knowledge Graph · AI Reasoning  │
│  Demographics · Ontology · Infrastructure · Voter Conversion · Twin  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Command Center | AC-level KPI dashboard: voter stats, issue intensity, political lean distribution, 2022 results, candidate roster, YouTube intelligence feed |
| `/booths` | Booth Intelligence | Searchable/filterable booth list with pulse scores, lean labels, and confidence ratings |
| `/booths/[id]` | Booth Detail | Full 10-panel booth card: history, pulse, issues, scheme gaps, narratives, contradictions, demographics |
| `/heatmap` | Constituency Heatmap | Interactive Leaflet map with geocoded booths coloured by BJP pulse, lean, or data quality |
| `/graph` | Knowledge Graph Explorer | Interactive D3/canvas 1-hop subgraph explorer for any entity (AC, Booth, Issue, Candidate, Party, Scheme) |
| `/reasoning` | AI Political Reasoning | Persistent chat interface: NL → Neo4j Cypher + DuckDuckGo/Wikipedia web search → Sarvam-30b synthesis |
| `/demographics` | Demographics | Voter composition breakdowns (gender, age segments) across all booths; booth-level election result rows |
| `/ontology` | Ontology Layer | Live Neo4j graph topology: node/relationship counts, active constraints, PG table row counts |
| `/infrastructure` | Data Infrastructure | PostgreSQL table stats + Neo4j graph coverage per booth (lat/lon present, in-graph, degree) |
| `/conversion` | Voter Conversion Engine | Beneficiary pipeline: identify scheme recipients, route field workers, track contact status per booth |
| `/twin` | Digital Twin | Snapshot view combining graph topology, heatmap readiness, narrative trends, and scheme delivery |

---

## FastAPI Endpoints (40+)

### Booth & AC Intelligence

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ac/{ac_id}/booths` | All booths with latest pulse scores |
| GET | `/booth/{id}/summary` | Full 10-panel booth summary card |
| GET | `/booth/{id}/pulse` | Pulse time-series (default 7d) |
| GET | `/booth/{id}/issues` | Top issues with polarity |
| GET | `/booth/{id}/comments` | Backing evidence feed |
| GET | `/booth/{id}/quality` | Data quality metrics + reasons |
| GET | `/booth/{id}/narratives` | Detected narrative patterns |
| GET | `/booth/{id}/contradictions` | Cross-source signal conflicts |
| GET | `/booth/{id}/segments` | Privacy-safe voter demographic segments |
| GET | `/booth/{id}/conversion` | Conversion opportunity scores for a booth |
| GET | `/ac/{ac_id}/candidates` | Candidate affidavits + sentiment |
| GET | `/ac/{ac_id}/schemes` | Aggregated scheme gap analysis |
| GET | `/ac/{ac_id}/narratives` | AC-level narrative trends |
| GET | `/ac/{ac_id}/events` | Political events timeline |
| GET | `/ac/{ac_id}/quality` | AC-level data quality summary |
| GET | `/ac/{ac_id}/recommendations` | Strategic risks, opportunities, and action items |
| GET | `/ac/{ac_id}/intel-summary` | Voter stats (PG) + issues/videos/candidates (Neo4j) |
| GET | `/ac/{ac_id}/intel` | Honest AC-level pulse (with attribution warnings) |
| GET | `/ac/{ac_id}/election-results` | AC-level results aggregated from booth_results |
| GET | `/ac/{ac_id}/booth-election-rows` | Per-booth per-party vote rows with turnout |
| GET | `/ac/{ac_id}/demographics/summary` | Voter demographics summary |
| GET | `/ac/{ac_id}/demographics/segments` | Booth-level demographic segments |
| GET | `/ac/{ac_id}/geo` | Geocoded booth positions with pulse scores |
| GET | `/ac/{ac_id}/heatmap-coverage` | Heatmap readiness KPI (default 85% geocoded target) |
| GET | `/ac/{ac_id}/twin-snapshot` | Ontology twin combining graph, heatmap, and segments |
| GET | `/ac/{ac_id}/graph-coverage` | Per-booth: PG lat/lon + Neo4j presence and degree |

### Graph & Ontology

| Method | Path | Description |
|--------|------|-------------|
| GET | `/graph/subgraph` | 1-hop subgraph from Neo4j around any entity |
| GET | `/ontology/status` | Live node/rel counts, constraints, PG table stats |
| GET | `/infrastructure/overview` | PG table row counts + Neo4j node/edge topology |

### AI Reasoning

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reasoning/query` | NL → Cypher → Neo4j + web search → Sarvam-30b synthesis |

### Chat Sessions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/chat/sessions` | List all reasoning sessions |
| POST | `/chat/sessions` | Create a new session |
| GET | `/chat/sessions/{id}` | Session metadata |
| GET | `/chat/sessions/{id}/messages` | All messages for a session |
| POST | `/chat/sessions/{id}/messages` | Append a message |
| PATCH | `/chat/sessions/{id}/title` | Rename a session |
| DELETE | `/chat/sessions/{id}` | Delete a session and all messages |

### Voter Conversion Engine

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ac/{ac_id}/conversion-overview` | Per-booth beneficiary + conversion funnel stats |
| GET | `/ac/{ac_id}/conversion-stats` | AC-level KPIs: total beneficiaries, targets, contacted |
| GET | `/booth/{id}/conversion-targets` | Route map for a booth's field worker |
| PATCH | `/beneficiaries/{id}/contact` | Mark a beneficiary as contacted |
| POST | `/beneficiaries/import` | Bulk-import beneficiary records |
| POST | `/ac/{ac_id}/conversion/seed-demo` | Seed synthetic beneficiary data for demo |

---

## 5 Intelligence Layers

| Layer | File | What it detects | Output |
|-------|------|----------------|--------|
| 1. Data Quality | `analytics/data_quality.py` | Source bias, geo resolution gaps, NLP confidence | `data_quality_metrics` + `DataQuality` node |
| 2. Scheme Gap | `analytics/scheme_gap_analysis.py` | execution / reach / awareness gap or performing_well | `scheme_gap_analysis` + `SchemeGap` node |
| 3. Alias Expansion | `nlp/alias_expander.py` | Unmatched location mentions → auto-proposes new aliases | Updates `gorakhpur_aliases.json` |
| 4. Contradiction Detection | `analytics/contradiction_detector.py` | YouTube vs News polarity divergence per entity | `contradiction_flags` + `ContradictionFlag` node |
| 5. Narrative Detection | `analytics/narrative_detector.py` | anti_incumbency / development / corruption / swing | `booth_narratives` + `Narrative` node |

### Scheme gap taxonomy

| `gap_type` | Condition | Meaning |
|-----------|-----------|---------|
| `execution_gap` | completed + high beneficiaries + negative sentiment | Reached people, still unhappy — quality problem |
| `reach_gap` | completed + low beneficiaries + negative sentiment | Not reaching intended recipients |
| `awareness_gap` | completed + high beneficiaries + neutral sentiment | Reached people, no credit signal |
| `performing_well` | completed + positive sentiment | Working as intended |
| `in_progress` | not completed | Cannot assess yet |
| `no_data` | < 3 sentiment events | Need more data |

### Narrative types

| `narrative_type` | Signal pattern |
|-----------------|---------------|
| `development_positive` | Positive events on roads/water/electricity |
| `anti_incumbency` | Ruling party scoring negative across ≥ 3 events |
| `corruption_narrative` | corruption issue surfacing |
| `price_rise_narrative` | prices/inflation issue surfacing |
| `women_safety_narrative` | women_safety/crime issue surfacing |
| `employment_crisis` | jobs/unemployment surfacing |
| `scheme_success` | Known scheme with positive sentiment |
| `swing_possible` | ≥ 2 MIXED_SIGNALS / SWING_INDICATOR contradiction pairs |

---

## Neo4j Graph Schema

### Core nodes

| Node | Key property | Description |
|------|-------------|-------------|
| `State` | `name` | Uttar Pradesh |
| `District` | `name` | Gorakhpur |
| `AssemblyConstituency` | `ac_id` | e.g. `GKP_322` |
| `Booth` | `booth_id` | e.g. `GKP_U_045` |
| `Candidate` | `candidate_id` | MyNeta affidavit data |
| `Party` | `name` | BJP, SP, BSP, INC |
| `Issue` | `code` | water, roads, jobs, corruption … |
| `Scheme` | `name` | PMAY, Ujjwala, MGNREGA … |
| `Panchayat` | `panchayat_id` | eGramSwaraj unit |
| `PulseEvent` | `event_id` | Single sentiment extraction |
| `Election` | `election_id` | 2017, 2022 results |

### Intelligence layer nodes

| Node | Key properties | Wires to |
|------|---------------|----------|
| `DataQuality` | `booth_id`, `quality_label`, `overall_quality_score`, `quality_reasons[]` | `Booth` via `HAS_QUALITY` |
| `Narrative` | `booth_id`, `narrative_type`, `strength`, `description` | `Booth` via `HAS_NARRATIVE`; `Issue`; `Party/Candidate` |
| `SchemeGap` | `booth_id`, `scheme_name`, `gap_type`, `gap_label`, `priority` | `Booth` via `HAS_SCHEME_GAP`; `Scheme`; `Issue` |
| `ContradictionFlag` | `booth_id`, `entity`, `source_a/b`, `delta`, `flag_label` | `Booth` via `HAS_CONTRADICTION`; `Party/Candidate` |

### Relationships

```
State    -[:HAS_DISTRICT]->        District
District -[:HAS_AC]->              AssemblyConstituency
AC       -[:HAS_BOOTH]->           Booth
Booth    -[:HAD_RESULT]->          BoothResult
Booth    -[:HAS_QUALITY]->         DataQuality
Booth    -[:HAS_NARRATIVE]->       Narrative
Booth    -[:HAS_SCHEME_GAP]->      SchemeGap
Booth    -[:HAS_CONTRADICTION]->   ContradictionFlag
Narrative-[:ABOUT_ISSUE]->         Issue
Narrative-[:INVOLVES_PARTY]->      Party
SchemeGap-[:FOR_SCHEME]->          Scheme
SchemeGap-[:TAGGED_ISSUE]->        Issue
PulseEvent-[:AT_BOOTH]->           Booth
Candidate-[:CONTESTED_IN]->        AssemblyConstituency
Candidate-[:REPRESENTS]->          Party
```

---

## NLP Pipeline (deterministic, multilingual)

```
Raw text (Hindi / Bhojpuri / English / mixed)
  → langdetect + Bhojpuri regex markers
  → Bhashini API (Bhojpuri→Hindi) | IndicTrans2 fallback
  → Groq llama-3.3-70b + Instructor (constrained JSON via Pydantic)
  → Rule-based fallback if confidence < 0.6
  → Geo-resolver: location_mention → booth_id via fuzzy match
  → Alias expander: unmatched mentions → gorakhpur_aliases.json
  → pulse_events table + PulseEvent nodes in Neo4j
```

### AI Reasoning pipeline

```
User question (natural language)
  → Cypher generation (Neo4j schema prompt + Groq/Sarvam)
  → Neo4j query → graph_results
  → DuckDuckGo HTML + Wikipedia API search → web_results
  → Sarvam-30b synthesis (primary) → Gemini (fallback) → plain summary
  → Response: answer, cypher, graph rows, web sources, mode, elapsed_ms
  → Persisted to chat_sessions / chat_messages in PostgreSQL
```

---

## Repo Structure

```
UP-ELection-Ontology-Engine/
├── api/
│   ├── main.py          ← 40+ FastAPI endpoints
│   ├── db.py
│   ├── queries.py       ← All SQL queries (PG + Neo4j)
│   ├── reasoning.py     ← AI reasoning pipeline (Sarvam/Gemini + Neo4j + web)
│   └── schemas.py
│
├── client_end/          ← Next.js 14 frontend (App Router)
│   └── app/
│       ├── page.tsx             ← Command Center dashboard
│       ├── booths/              ← Booth list + detail pages
│       ├── heatmap/             ← Leaflet geospatial map
│       ├── graph/               ← Knowledge graph explorer
│       ├── reasoning/           ← AI chat interface (persistent sessions)
│       ├── demographics/        ← Voter demographics
│       ├── ontology/            ← Ontology layer status
│       ├── infrastructure/      ← Data infrastructure monitor
│       ├── conversion/          ← Voter conversion engine
│       └── twin/                ← Digital twin snapshot
│
├── nlp/                 ← 7-stage multilingual NLP pipeline
│   ├── pipeline.py
│   ├── lang_detect.py
│   ├── bhashini.py
│   ├── extractor.py
│   ├── rule_classifier.py
│   ├── geo_resolver.py
│   ├── alias_expander.py
│   └── schemas.py
│
├── analytics/
│   ├── booth_metrics.py
│   ├── data_quality.py
│   ├── scheme_gap_analysis.py
│   ├── contradiction_detector.py
│   ├── narrative_detector.py
│   └── historical_analysis.py
│
├── graph/
│   ├── constraints.cypher
│   ├── constraints_v2.cypher
│   ├── loaders/
│   │   ├── load_structure.py
│   │   ├── load_booths.py
│   │   ├── load_candidates.py
│   │   ├── load_panchayats.py
│   │   ├── load_pulse_events.py
│   │   └── load_quality_narratives.py
│   └── queries/
│       └── cypher_lib.py
│
├── etl/                 ← 20+ ETL scripts
│   ├── ingest_eroll_data.py
│   ├── ingest_political_data.py
│   ├── ingest_tcpd_voteshare.py
│   ├── ingest_youtube_videos.py
│   ├── aggregate_eroll_segments.py
│   ├── aggregate_form20_results.py
│   ├── compute_booth_election_metrics.py
│   ├── process_youtube_signals.py
│   ├── stage_news_to_pulse.py
│   ├── stage_youtube_to_pulse.py
│   ├── transform_candidates.py
│   ├── transform_census.py
│   ├── transform_geography.py
│   ├── transform_schemes.py
│   └── pulse_event_prep.py
│
├── ingestion/           ← Per-source scrapers
│   ├── eci_booths.py
│   ├── myneta_candidates.py
│   ├── eci_booth_results.py
│   ├── egramswaraj_schemes.py
│   ├── youtube_comments.py
│   ├── youtube_videos.py
│   ├── news_scraper.py
│   ├── multi_news_scraper.py
│   ├── electoral_demographics.py
│   └── grievance_scraper.py
│
├── dashboard/           ← Legacy Streamlit dashboard (standalone)
│   ├── app.py
│   └── pages/
│
├── flows/               ← Prefect orchestration flows
│   ├── nlp/flow_sentiment.py
│   ├── graph/flow_load_graph.py
│   └── aggregation/
│       ├── flow_booth_metrics.py
│       └── flow_full_analytics.py
│
├── db/migrations/
│   ├── 001_initial.sql          ← 14 core tables
│   └── 002_quality_narratives.sql
│
├── data/seeds/
│   ├── gorakhpur_aliases.json   ← locality → booth_id (auto-expanded)
│   └── political_lexicon.json
│
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

---

## Key Metrics per Booth

| Metric | Formula | Source |
|--------|---------|--------|
| BJP Pulse Score | `Σ(polarity × confidence × source_weight) / Σ(weights)` | pulse_events |
| Opposition Pulse | Same for SP/BSP/INC | pulse_events |
| Digital Lean | `bjp_pulse - opp_pulse` → label: STRONG_BJP / LEAN_BJP / NEUTRAL / LEAN_OPP / STRONG_OPP | computed |
| Top Issues | Weighted issue count, ranked | pulse_events |
| Issue Momentum | `(last_7d_count - prev_7d_count) / prev_7d_count` | pulse_events |
| Data Quality Score | `0.25×volume + 0.25×geo + 0.30×nlp + 0.20×diversity` | data_quality_metrics |
| Scheme Gap Type | 4-way classification (execution/reach/awareness/well) | scheme_gap_analysis |
| Consistency Score | `1 - |polarity_a - polarity_b| / 2` | contradiction_flags |
| Narrative Strength | Weighted issue/party signal share | booth_narratives |
| Historical Trend | Vote share delta across elections | booth_results |

Source weights: survey=1.0 · field_note=0.9 · youtube=0.6 · news=0.4

---

## Election Completeness & Null Policies

The engine supports complete historical datasets (2017/2022 Vidhan Sabha) and partially available datasets (2024 Lok Sabha) via a PostgreSQL-first null policy:

### Completeness taxonomy

Each row in the candidate results fact table (`candidate_party_history`) carries a `result_completeness_status`:
- `'complete'` — all contesting candidates have confirmed vote totals and ranks
- `'winner_runnerup_only'` — only winner (rank 1) and runner-up (rank 2) have vote counts; all other `NULL`
- `'partial'` — temporal stubs or elections where vote totals are not yet seeded

### Null rules
- **Missing votes**: remain `NULL` rather than zero-padded
- **Derived metrics**: vote share percentages and margins remain `NULL` when inputs are missing
- **Query grain**: strictly `candidate_id + election_year + constituency_id + election_type` — no runtime `GROUP BY`

### QA audits
`scripts/verify_election_results_qa.py` enforces:
- Winner uniqueness (max one winner per constituency-year)
- Monotonic vote ordering (winners > runners-up descending)
- Null policy adherence per completeness state

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Relational DB | PostgreSQL 16 (Neon.tech / local Docker) |
| Graph DB | Neo4j 5 (AuraDB Free or local Docker) |
| Cache | Redis 7 (Upstash / local Docker) |
| Orchestration | Prefect 3 |
| NLP Extraction | Groq llama-3.3-70b + Instructor (Pydantic-constrained JSON) |
| Translation | Bhashini API (Hindi/Bhojpuri, free govt API) |
| AI Reasoning | Sarvam-30b (primary) → Gemini (fallback) |
| Web Search | DuckDuckGo HTML + Wikipedia API |
| API | FastAPI + Uvicorn |
| Frontend | Next.js 14 (App Router), Recharts, React-Leaflet, Lucide |
| Legacy Dashboard | Streamlit (standalone, `dashboard/`) |

---

## Quickstart

### 1. Clone & Python environment

```bash
git clone git@github.com:Aryan-en/UP-ELection-Ontology-Engine.git
cd UP-ELection-Ontology-Engine
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # fill in API keys
```

Set `SARVAM_API_KEY` in `.env` for AI reasoning. Falls back to `GEMINI_API_KEY` if absent.

### 2. Start local infrastructure

```bash
docker-compose up -d
# Postgres :5432 · Neo4j :7474/:7687 · Redis :6379
```

### 3. Initialize databases

```bash
psql $POSTGRES_URL -f db/migrations/001_initial.sql
psql $POSTGRES_URL -f db/migrations/002_quality_narratives.sql
psql $POSTGRES_URL -f db/seeds/seed_issues.sql

cat graph/constraints.cypher    | cypher-shell -u neo4j -p $NEO4J_PASSWORD
cat graph/constraints_v2.cypher | cypher-shell -u neo4j -p $NEO4J_PASSWORD
```

### 4. Run ingestion

```bash
python -m ingestion.eci_booths
python -m ingestion.myneta_candidates
python -m ingestion.eci_booth_results
python -m ingestion.youtube_comments
python -m ingestion.news_scraper
```

### 5. Run NLP + graph load

```bash
python -m flows.nlp.flow_sentiment
python -m flows.graph.flow_load_graph
```

### 6. Run full analytics pipeline

```bash
# All 5 intelligence layers in dependency order
python -m flows.aggregation.flow_full_analytics
```

### 7. Start API

```bash
uvicorn api.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

### 8. Start Next.js frontend

```bash
cd client_end
npm install
npm run dev
# http://localhost:3000
```

---

## Data Sources

| Source | What | Priority | Script |
|--------|------|----------|--------|
| CEO UP / ECI | Booth master, AC list | P0 | `ingestion/eci_booths.py` |
| MyNeta / ADR | Candidate affidavits | P0 | `ingestion/myneta_candidates.py` |
| ECI Results Archives | Historical booth results | P1 | `ingestion/eci_booth_results.py` |
| eGramSwaraj | Panchayat scheme delivery | P1 | `ingestion/egramswaraj_schemes.py` |
| YouTube (yt-dlp) | Comments + videos on political content | P1 | `ingestion/youtube_videos.py` |
| Jagran / Amar Ujala | Local news articles | P1 | `ingestion/news_scraper.py` |
| Electoral Roll (PDF) | Voter demographics per booth | P1 | `etl/ingest_eroll_data.py` |
| TCPD Vote Share | Historical vote share data | P2 | `etl/ingest_tcpd_voteshare.py` |
| KoBoToolbox | Field surveys | P2 | manual → ETL |
| MGNREGA / PMAY | Beneficiary data | P2 | `etl/load_real_schemes.py` |

---

## Security & Compliance

- **Electoral Roll Privacy:** No PII stored; only aggregated demographic counts per booth.
- **Data Encryption:** Sensitive data encrypted at rest and in transit.
- **Access Control:** Role-based permissions (admin, analyst, campaign manager).
- **Audit Trail:** Full versioning of data updates and user actions.
- **Legal Compliance:** Designed within RPA 1951 election law constraints.

---

## Success Metrics

- **Coverage:** Booth-level data for entire AC(s).
- **Sentiment Accuracy:** NLP confidence > 85% on ground-truth validation.
- **Data Freshness:** Daily sentiment pulse updates.
- **Prediction Power:** Pre-election booth-level sentiment vs. actual results correlation > 0.75.

---

## Roadmap

- **Phase 1 (complete):** Gorakhpur Urban AC — ~300 booths, core engine, Next.js frontend
- **Phase 2:** Add Campierganj AC (2nd AC)
- **Phase 3:** Scale to full Gorakhpur district (4+ ACs)
- **Phase 4:** Expand to other UP districts
- **Phase 5:** Real-time WhatsApp/SMS campaign delivery integration

---

## Contributing

This is a closed-source strategic tool. Access is restricted to core team members and authorized party functionaries.

---

## Documentation

| File | Purpose |
|------|---------|
| `docs/setup.md` | Local environment setup |
| `docs/ETL_NEO4J_PIPELINE.md` | ETL → Neo4j pipeline details |
| `docs/MODULE_REFERENCE.md` | Module-by-module reference |
| `gorakhpur-master-plan.md` | Full 5-week plan, all 15 roles, all data sources |
| `gorakhpur-5day-sprint.md` | 5-day demo sprint with runnable code |
| `DATA_SOURCES.md` | Source inventory and ingestion notes |
