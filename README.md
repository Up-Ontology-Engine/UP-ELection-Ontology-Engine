# UP Election Ontology Engine — Gorakhpur Booth Intelligence Platform

**Mission: Win Elections Through Hyper-Local Intelligence**

A booth-level political intelligence platform for Gorakhpur Urban AC-322 (UP Vidhan Sabha). Combines a Neo4j knowledge graph, real Form-20 election data, MyNeta affidavit profiles with live web-researched digital presence, a multilingual NLP pipeline, and a 12-page Next.js frontend delivering analyst-grade insights down to individual polling booths.

> Gorakhpur Urban AC-322 · 179 booths · 1,14,326 registered voters · Hindi / Bhojpuri / English · PostgreSQL + Neo4j + Next.js

---

## What This Builds

```
Booth 45 (Gorakhpur Urban AC-322)
├── Form-20 (2022): BJP 58% · SP 21% · BSP 8%  → LEAN_BJP
├── Digital Lean: bjp_pulse_score +0.54, opp_pulse_score -0.61
├── Confidence: HIGH (real election turnout: 712 voters)
├── Data Quality: MEDIUM — 78% EPIC coverage | geocoded
├── Top Issues: Water +22%  |  Roads +14%  |  Jobs +10%
├── Scheme Gap: PMAY → reach_gap (low beneficiaries, negative sentiment)
├── Dominant Narrative: anti_incumbency (strength 0.62)
├── Mixed Signal: YouTube +0.4 vs News -0.3 → SWING_INDICATOR
├── Candidate: Adityanath (BJP) · 66.18% share · ₹1.54 Cr assets · 0 cases
│   Digital Presence: 32.6M Twitter · 17M Instagram · 12M Facebook
└── Recommendation: Focus on water supply + youth jobs outreach
```

Every field is backed by real data: ECI booth master (PoolBoothData PDF→JSON, 179 parts), Form-20 election results, MyNeta affidavits + live web research, eGramSwaraj schemes, YouTube comments — flowing through a deterministic multilingual NLP pipeline into Neo4j with 5 intelligence layers.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  REAL DATA SOURCES                                                   │
│  PoolBoothData_JSON (179-part 2026 electoral roll)                  │
│  Form20_JSON (AC322 2022/2017 election results — per-booth votes)   │
│  Myneta/ (affidavit JSONs: 2017, 2022, 2024 LS)                     │
│  eGramSwaraj · YouTube Comments · Local News · Field Surveys        │
└─────────────────────────────────────────────────────────────────────┘
                              │  ingestion/
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  POSTGRES (gorakhpur_db)                                             │
│  booth_master (179 rows) · booth_metrics · ac_metrics               │
│  ac_demographics · data_quality_metrics · booth_results             │
│  booth_panchayat_mapping · panchayat_master                         │
│  ── Intelligence ──                                                  │
│  booth_narratives · contradiction_flags · scheme_gap_analysis       │
│  ── Chat / Conversion ──                                             │
│  chat_sessions · chat_messages · scheme_beneficiaries               │
└─────────────────────────────────────────────────────────────────────┘
                              │  nlp/pipeline.py
                              │  lang_detect → bhashini → groq → geo_resolve
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  NEO4J  — Full Property Graph                                        │
│  State→District→AC→Booth→Candidate→Party→Issue→PulseEvent→Scheme   │
│  DataQuality · Narrative · SchemeGap · ContradictionFlag nodes      │
│  24 active constraints/indexes                                       │
└─────────────────────────────────────────────────────────────────────┘
                              │  analytics/ + graph/loaders/
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FASTAPI  (40+ endpoints)                                            │
│  Booths · Pulse · Issues · Quality · Narratives · Contradictions    │
│  Candidates · Schemes · Demographics · Graph · Heatmap · Reasoning  │
│  Conversion Engine · Chat Sessions · Digital Twin                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  NEXT.JS 14 FRONTEND  (12 pages, App Router)                         │
│  Command Center · Booths · Heatmap · Knowledge Graph                │
│  My Neta Report Card · AI Reasoning · Demographics                  │
│  Ontology · Infrastructure · Voter Conversion · Digital Twin        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Command Center | AC-level KPIs: voter stats, Form-20 lean distribution, issue intensity, 2022 results, booth roster, YouTube intelligence feed |
| `/booths` | Booth Intelligence | Searchable/filterable booth list with BJP/SP pulse scores, lean labels, confidence ratings |
| `/booths/[id]` | Booth Detail | Full 10-panel booth card: Form-20 history, pulse, issues, scheme gaps, narratives, contradictions, demographics |
| `/heatmap` | Constituency Heatmap | Interactive Leaflet map — 179 booths coloured by BJP pulse, lean label, KG coverage, or data quality confidence. Slide-in analysis panel per booth. |
| `/graph` | Knowledge Graph Explorer | Interactive D3/canvas 1-hop subgraph explorer for any entity (AC, Booth, Issue, Candidate, Party, Scheme) |
| `/myneta` | My Neta Report Card | Candidate knowledge graph from 51 MyNeta affidavit profiles (2017, 2022 VS + 2024 LS). Search by name/party. 10-section deep dossier per candidate including web-researched **Digital Presence** (Twitter/X, Facebook, Instagram, YouTube, Wikipedia). |
| `/reasoning` | AI Political Reasoning | Persistent chat: NL → Neo4j Cypher + DuckDuckGo/Wikipedia → Sarvam-30b synthesis |
| `/demographics` | Demographics | Gender + age-segment voter breakdown across all booths; booth-level election result rows |
| `/ontology` | Ontology Layer | Live Neo4j topology: node/rel counts, 24 active constraints, PG table row counts |
| `/infrastructure` | Data Infrastructure | PostgreSQL table stats + Neo4j graph coverage per booth (geocoded, in-graph, degree) |
| `/conversion` | Voter Conversion Engine | Beneficiary pipeline: scheme recipients → field worker routing → contact tracking per booth |
| `/twin` | Digital Twin | Snapshot combining graph topology, heatmap readiness, narrative trends, and scheme delivery |

---

## FastAPI Endpoints (40+)

### Booth & AC Intelligence

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ac/{ac_id}/booths` | All 179 booths with latest Form-20 pulse scores |
| GET | `/booth/{id}/summary` | Full 10-panel booth summary card |
| GET | `/booth/{id}/pulse` | Pulse time-series (default 7d) |
| GET | `/booth/{id}/issues` | Top issues with polarity |
| GET | `/booth/{id}/comments` | Backing evidence feed |
| GET | `/booth/{id}/quality` | Data quality metrics + reasons |
| GET | `/booth/{id}/narratives` | Detected narrative patterns |
| GET | `/booth/{id}/contradictions` | Cross-source signal conflicts |
| GET | `/booth/{id}/segments` | Privacy-safe voter demographic segments |
| GET | `/booth/{id}/conversion` | Conversion opportunity scores |
| GET | `/ac/{ac_id}/candidates` | Candidate affidavits + sentiment |
| GET | `/ac/{ac_id}/schemes` | Aggregated scheme gap analysis |
| GET | `/ac/{ac_id}/narratives` | AC-level narrative trends |
| GET | `/ac/{ac_id}/events` | Political events timeline |
| GET | `/ac/{ac_id}/quality` | AC-level data quality summary |
| GET | `/ac/{ac_id}/recommendations` | Strategic risks, opportunities, action items |
| GET | `/ac/{ac_id}/intel-summary` | Voter stats (PG) + issues/videos/candidates (Neo4j) |
| GET | `/ac/{ac_id}/intel` | Honest AC-level pulse (with attribution warnings) |
| GET | `/ac/{ac_id}/election-results` | AC-level 2022/2017 results from booth_results |
| GET | `/ac/{ac_id}/booth-election-rows` | Per-booth per-party vote rows with turnout |
| GET | `/ac/{ac_id}/demographics/summary` | Voter demographics summary |
| GET | `/ac/{ac_id}/demographics/segments` | Booth-level demographic segments |
| GET | `/ac/{ac_id}/geo` | Geocoded booth positions with pulse scores |
| GET | `/ac/{ac_id}/heatmap-coverage` | Heatmap readiness KPI |
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
| POST | `/ac/{ac_id}/conversion/seed-demo` | Seed demo beneficiary data |

---

## Data — What's Real

### Electoral Roll (PoolBoothData_JSON)
- **179 voter roll parts** (Parts 1–190, 11 skipped) from 2026 SIR Revision of AC-322
- **1,14,326 registered voters** with gender + age breakdown per booth
- Fields: `voter_id`, `name`, `age`, `gender`, `photo_flag`, `epic_id`
- Ingested by `ingestion/ingest_poolboothdata.py` → Postgres `booth_master` + Neo4j

### Form-20 Election Results (Form20_JSON)
- **AC322.json** — 471 polling stations, 15 candidates, 2022 UP Vidhan Sabha
- Per-booth vote counts for BJP, SP, BSP, INC, independents
- Used by `ingestion/ingest_form20_lean.py` → `booth_metrics.digital_lean_label`
- **AC322.json** result: 150 STRONG_BJP · 19 LEAN_BJP · 8 STRONG_OPP · 3 NEUTRAL · 1 LEAN_OPP

### MyNeta Candidate Profiles (data/Myneta/)
- `myneta_GKP_322_2022.json` — 12 candidates (includes Adityanath, Subhawati Shukla SP, Chandra Shekhar ASP)
- `myneta_GKP_322_2017.json` — 21 candidates (includes Dr. Radha Mohan Das Agrawal BJP, Janardan Choudhari BSP)
- `myneta_GKP_LS64_2024.json` — 2024 Lok Sabha Gorakhpur candidates (Ravi Kishan BJP winner)
- **51 enriched profiles** in `client_end/app/myneta/complete_candidate_data.json`
  - 10-section dossier per candidate: Personal Vitals → Digital Presence
  - Digital Presence includes: Twitter/X handle + followers, Facebook, Instagram, YouTube, Wikipedia

### Geocoding
- 30 booths have real lat/lon coordinates (geocoded from locality names)
- 149 booths use deterministic synthetic coordinates (grid + jitter within Gorakhpur Urban bounds)
- Bounds: lat 26.67–26.80, lon 83.34–83.42

---

## 5 Intelligence Layers

| Layer | File | What it detects | Output |
|-------|------|----------------|--------|
| 1. Data Quality | `analytics/data_quality.py` | EPIC/photo/age/gender completeness per booth | `data_quality_metrics` + `DataQuality` Neo4j node |
| 2. Scheme Gap | `analytics/scheme_gap_analysis.py` | Execution / reach / awareness gap or performing_well | `scheme_gap_analysis` + `SchemeGap` node |
| 3. Alias Expansion | `nlp/alias_expander.py` | Unmatched location mentions → auto-propose new aliases | Updates `gorakhpur_aliases.json` |
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
| `corruption_narrative` | Corruption issue surfacing |
| `price_rise_narrative` | Prices/inflation issue surfacing |
| `women_safety_narrative` | Women safety/crime issue surfacing |
| `employment_crisis` | Jobs/unemployment surfacing |
| `scheme_success` | Known scheme with positive sentiment |
| `swing_possible` | ≥ 2 MIXED_SIGNALS / SWING_INDICATOR contradiction pairs |

---

## Neo4j Graph Schema

### Core nodes

| Node | Key property | Description |
|------|-------------|-------------|
| `State` | `name` | Uttar Pradesh |
| `District` | `name` | Gorakhpur |
| `AssemblyConstituency` | `ac_id` | `GKP_322` |
| `Booth` | `booth_id` | e.g. `GKP_322_001` … `GKP_322_190` |
| `Candidate` | `candidate_id` | MyNeta affidavit data (51 profiles) |
| `Party` | `name` | BJP, SP, BSP, INC, AAP, ASP … |
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

### My Neta web enrichment pipeline

```
Candidate name (from Myneta JSON)
  → Web search: "[Name] [party] [constituency] politician"
  → Extract: bio, DOB, family, education, career, assets, criminal cases
  → Social media: Twitter/X handle + followers, Facebook page, Instagram,
                  YouTube channel, Wikipedia URL
  → Stored in analytics/merge_web_enrichment.py → complete_candidate_data.json
  → Served as 10-section profile in /myneta CandidateDialogue modal
```

---

## Repo Structure

```
UP-ELection-Ontology-Engine/
│
├── api/
│   ├── main.py          ← 40+ FastAPI endpoints
│   ├── db.py            ← PG + Neo4j connection factories
│   ├── queries.py       ← All SQL + Cypher queries
│   ├── reasoning.py     ← AI reasoning pipeline (Sarvam/Gemini + Neo4j + web)
│   └── schemas.py       ← Pydantic response models
│
├── client_end/          ← Next.js 14 App Router frontend
│   ├── app/
│   │   ├── page.tsx                  ← Command Center
│   │   ├── DashboardCharts.tsx       ← Party pulse chart
│   │   ├── globals.css               ← CSS variables design system
│   │   ├── layout.tsx                ← Root layout + ThemeProvider
│   │   ├── booths/                   ← Booth list + [id] detail
│   │   ├── heatmap/
│   │   │   ├── page.tsx              ← SSR wrapper
│   │   │   ├── HeatMapClient.tsx     ← Client component + analysis panel
│   │   │   └── LeafletMap.tsx        ← Vanilla Leaflet (SSR-safe via dynamic())
│   │   ├── graph/
│   │   │   ├── page.tsx              ← Suspense wrapper (fixes useSearchParams)
│   │   │   └── GraphCanvas.tsx       ← D3 force simulation canvas
│   │   ├── myneta/
│   │   │   ├── page.tsx              ← Graph canvas + search bar + party stats
│   │   │   ├── CandidateDossier.tsx  ← Slide-in report card
│   │   │   ├── CandidateDialogue.tsx ← Full 10-section modal + Digital Presence
│   │   │   ├── complete_candidate_data.json ← 51 enriched profiles (web-researched)
│   │   │   └── candidate_enrichment.json
│   │   ├── reasoning/                ← Persistent AI chat interface
│   │   ├── demographics/             ← Voter demographics + election rows
│   │   ├── ontology/                 ← Neo4j topology + constraint viewer
│   │   ├── infrastructure/           ← PG table stats + Neo4j coverage
│   │   ├── conversion/               ← Voter conversion engine
│   │   └── twin/                     ← Digital twin snapshot
│   ├── components/
│   │   ├── LeanBadge.tsx             ← Party label chip (BJP/SP/BSP/Neutral)
│   │   ├── PulseBar.tsx              ← BJP vs SP signal bar
│   │   ├── Header.tsx                ← Executive briefing bar
│   │   ├── Sidebar.tsx               ← Navigation sidebar
│   │   └── ThemeProvider.tsx         ← Dark/light theme context
│   └── lib/
│       └── api.ts                    ← All typed fetch helpers + interfaces
│
├── nlp/                 ← 7-stage multilingual NLP pipeline
│   ├── pipeline.py, lang_detect.py, bhashini.py
│   ├── extractor.py, rule_classifier.py
│   ├── geo_resolver.py, alias_expander.py, schemas.py
│
├── analytics/
│   ├── data_quality.py               ← Layer 1: EPIC/photo/age completeness
│   ├── scheme_gap_analysis.py        ← Layer 2: Scheme execution/reach/awareness gaps
│   ├── contradiction_detector.py     ← Layer 4: YouTube vs News polarity conflicts
│   ├── narrative_detector.py         ← Layer 5: anti_incumbency/development/swing
│   ├── booth_metrics.py              ← Booth-level pulse aggregation
│   ├── historical_analysis.py        ← Vote share trend analysis
│   ├── conversion_opportunity.py     ← Beneficiary → conversion scoring
│   ├── myneta_graph.py               ← Build MyNeta KG JSON for /myneta
│   ├── myneta_complete_enrichment.py ← Auto-generate 10-section profiles from affidavits
│   ├── merge_web_enrichment.py       ← Merge web-researched data into profiles
│   └── geo_resolver_batch.py         ← Batch geocoding for booth coordinates
│
├── ingestion/           ← Data ingestion scripts
│   ├── ingest_poolboothdata.py       ← PoolBoothData PDF→JSON→PG→Neo4j (179 booths)
│   ├── ingest_all_features.py        ← Master pipeline: demographics, quality, metrics
│   ├── ingest_form20_lean.py         ← Form-20 AC322.json → booth_metrics lean labels
│   ├── myneta_candidates.py          ← MyNeta scraper
│   ├── myneta_export_json.py         ← Export affidavit data to Myneta/ JSONs
│   ├── eci_booths.py                 ← ECI booth master
│   ├── eci_booth_results.py          ← ECI historical results
│   ├── egramswaraj_schemes.py        ← eGramSwaraj scheme delivery
│   ├── youtube_comments.py           ← YouTube comment ingestion
│   └── news_scraper.py               ← Jagran/Amar Ujala news
│
├── graph/
│   ├── constraints.cypher            ← 24 Neo4j constraints/indexes
│   ├── constraints_v2.cypher         ← Intelligence layer constraints
│   └── loaders/
│       ├── load_voter_graph.py       ← Voter→Household→Booth Neo4j loader
│       ├── load_structure.py, load_booths.py
│       ├── load_candidates.py, load_panchayats.py
│       ├── load_pulse_events.py, load_quality_narratives.py
│
├── data/
│   ├── PoolBoothData_JSON/           ← 179 part_*.json voter roll files
│   ├── Form20_JSON/                  ← AC322.json + 322 (1-4).json election results
│   ├── Myneta/                       ← myneta_GKP_322_2022.json, 2017.json, LS64_2024.json
│   ├── gorakhpur_grievance_only/     ← Grievance records
│   └── seeds/                        ← gorakhpur_aliases.json, political_lexicon.json
│
├── db/migrations/
│   ├── 001_initial.sql               ← 14 core PG tables
│   └── 002_quality_narratives.sql    ← Intelligence layer tables
│
├── flows/               ← Prefect orchestration flows
│   ├── nlp/flow_sentiment.py
│   ├── graph/flow_load_graph.py
│   └── aggregation/flow_full_analytics.py
│
├── etl/                 ← Transform + aggregate scripts
├── dashboard/           ← Legacy Streamlit dashboard
├── scripts/             ← QA and utility scripts
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

---

## Key Metrics per Booth

| Metric | Formula | Source |
|--------|---------|--------|
| BJP Pulse Score | Vote share normalized: `(bjp_votes / total_valid) * 2 - 1` (range -1 to +1) | Form-20 / pulse_events |
| Opp Pulse Score | Same for SP + BSP combined | Form-20 / pulse_events |
| Digital Lean | `bjp_pulse - opp_pulse` → STRONG_BJP / LEAN_BJP / NEUTRAL / LEAN_OPP / STRONG_OPP | Derived |
| Top Issues | Weighted issue count, ranked | pulse_events |
| Issue Momentum | `(last_7d_count - prev_7d_count) / prev_7d_count` | pulse_events |
| Data Quality Score | `0.45×epic_rate + 0.35×age_rate + 0.20×photo_rate` | data_quality_metrics |
| Scheme Gap Type | 4-way: execution / reach / awareness / performing_well | scheme_gap_analysis |
| Consistency Score | `1 - \|polarity_a - polarity_b\| / 2` | contradiction_flags |
| Narrative Strength | Weighted issue/party signal share | booth_narratives |
| Historical Trend | Vote share delta across 2017→2022 | booth_results |

Signal source weights: survey=1.0 · field_note=0.9 · youtube=0.6 · news=0.4

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Relational DB | PostgreSQL 16 (Neon.tech serverless / local Docker) |
| Graph DB | Neo4j 5 (AuraDB Free / local Docker) — 24 active constraints |
| Cache | Redis 7 (Upstash / local Docker) |
| Orchestration | Prefect 3 |
| NLP Extraction | Groq llama-3.3-70b + Instructor (Pydantic-constrained JSON) |
| Translation | Bhashini API (Hindi/Bhojpuri, free GOI API) |
| AI Reasoning | Sarvam-30b (primary) → Gemini (fallback) |
| Web Search | DuckDuckGo HTML + Wikipedia API + Claude web search (candidate enrichment) |
| API | FastAPI + Uvicorn |
| Frontend | Next.js 14 (App Router), Recharts, Vanilla Leaflet, Lucide Icons |
| Map | Leaflet.js (vanilla, not react-leaflet — SSR-safe via Next.js `dynamic()`) |
| Knowledge Graph UI | D3.js force simulation on HTML5 Canvas |
| Legacy Dashboard | Streamlit (standalone, `dashboard/`) |

---

## Quickstart

### 1. Clone & Python environment

```bash
git clone git@github.com:Aryan-en/UP-ELection-Ontology-Engine.git
cd UP-ELection-Ontology-Engine
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # fill: POSTGRES_URL, NEO4J_URI, NEO4J_PASSWORD,
                               #       SARVAM_API_KEY, GEMINI_API_KEY, GROQ_API_KEY
```

### 2. Start local infrastructure

```bash
docker-compose up -d
# PostgreSQL :5432 · Neo4j :7474/:7687 · Redis :6379
```

### 3. Initialize databases

```bash
psql $POSTGRES_URL -f db/migrations/001_initial.sql
psql $POSTGRES_URL -f db/migrations/002_quality_narratives.sql

cat graph/constraints.cypher    | cypher-shell -u neo4j -p $NEO4J_PASSWORD
cat graph/constraints_v2.cypher | cypher-shell -u neo4j -p $NEO4J_PASSWORD
```

### 4. Ingest real data (order matters)

```bash
# Step 1 — Voter roll → booth_master (179 booths, 1,14,326 voters)
python -m ingestion.ingest_poolboothdata

# Step 2 — Demographics, data quality, ac_metrics, panchayat mapping
python -m ingestion.ingest_all_features

# Step 3 — Form-20 real election results → booth_metrics lean labels
python -m ingestion.ingest_form20_lean

# Step 4 — MyNeta affidavit profiles → Myneta/ JSON files
python -m ingestion.myneta_export_json
```

### 5. Build analytics & graph

```bash
# Neo4j voter graph (Voter→Household→Section→Booth)
python -m graph.loaders.load_voter_graph

# MyNeta KG (Candidate→Party→Constituency)
python -m analytics.myneta_graph

# Web-enrich all 51 candidate profiles with digital presence data
python -m analytics.merge_web_enrichment

# Copy to Next.js public dir
cp data/Myneta/myneta_graph.json client_end/public/myneta_graph.json
```

### 6. Run NLP + full analytics pipeline

```bash
python -m flows.nlp.flow_sentiment
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

| Source | What | Actual files | Script |
|--------|------|-------------|--------|
| CEO UP / ECI Electoral Roll | 179-booth voter roll (179 parts, 1,14,326 voters) | `PoolBoothData_JSON/part_*.json` | `ingestion/ingest_poolboothdata.py` |
| ECI Form-20 Results | Per-booth vote counts 2022/2017 (AC322, 471 polling stations) | `Form20_JSON/AC322.json` | `ingestion/ingest_form20_lean.py` |
| MyNeta / ADR | Candidate affidavits — 51 profiles across 2017/2022/2024 | `data/Myneta/myneta_*.json` | `ingestion/myneta_export_json.py` |
| Web Research | Candidate digital presence (Twitter, Facebook, Instagram, YouTube) | `complete_candidate_data.json` | `analytics/merge_web_enrichment.py` |
| eGramSwaraj | Panchayat scheme delivery records | — | `ingestion/egramswaraj_schemes.py` |
| YouTube (yt-dlp) | Comments + videos on political content | — | `ingestion/youtube_comments.py` |
| Jagran / Amar Ujala | Local news articles | — | `ingestion/news_scraper.py` |
| TCPD Vote Share | Historical vote share data | — | `etl/ingest_tcpd_voteshare.py` |
| KoBoToolbox | Field surveys | manual → ETL | — |
| MGNREGA / PMAY | Beneficiary data | — | `etl/load_real_schemes.py` |

---

## Gorakhpur Urban AC-322 — Key Facts

| Stat | Value |
|------|-------|
| Booth count | 179 (part numbers 1–190, 11 skipped) |
| Registered voters | 1,14,326 (2026 SIR revision) |
| Gender split | Male ~55% · Female ~45% |
| 2022 Winner | Yogi Adityanath (BJP) — 1,65,499 votes (66.18%) |
| 2022 Runner-up | Subhawati Upendra Dutt Shukla (SP) — 62,109 votes (24.84%) |
| 2022 Total valid votes | ~2,50,000 across 471 polling stations |
| BJP lean (Form-20 based) | 150 STRONG_BJP · 19 LEAN_BJP · 8 STRONG_OPP · 3 NEUTRAL · 1 LEAN_OPP |
| Geocoded booths | 30 real lat/lon · 149 synthetic within bounds |
| Neo4j constraints | 24 active |
| MyNeta profiles | 51 (2017 VS: 21 · 2022 VS: 12 · 2024 LS: 12 + new) |

---

## Security & Compliance

- **Electoral Roll Privacy:** No PII stored; only aggregated demographic counts per booth.
- **Data Encryption:** Sensitive data encrypted at rest and in transit.
- **Access Control:** Role-based permissions (admin, analyst, campaign manager).
- **Audit Trail:** Full versioning of data updates and user actions.
- **Legal Compliance:** Designed within RPA 1951 election law constraints.

---

## Roadmap

- **Phase 1 (complete):** Gorakhpur Urban AC-322 — 179 booths, 51 candidate profiles, 12-page frontend, Form-20 lean ingestion, candidate digital presence research
- **Phase 2:** Add Campierganj AC-326 (2nd AC, same district)
- **Phase 3:** Scale to full Gorakhpur district (4+ ACs)
- **Phase 4:** Real-time WhatsApp/SMS campaign delivery integration
- **Phase 5:** Expand to other UP districts + 2027 UP Vidhan Sabha prep

---

## Contributing

Closed-source strategic tool. Access restricted to core team members and authorised party functionaries.
