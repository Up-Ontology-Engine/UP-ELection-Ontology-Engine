to# Module Reference — UP Election Ontology Engine

> Gorakhpur Political Intelligence OS — component-by-component guide  
> Pilot AC: Gorakhpur Urban (GKP_322) | Stack: PostgreSQL · Neo4j · Redis · FastAPI · Streamlit

---

## Data Directory Layout

```
data/
├── raw/                    # Source files — never modified after ingestion
│   ├── 2022/
│   │   └── form20/         # ECI Form-20 XLS (booth-level vote counts per candidate)
│   └── 2025/               # Future cycle placeholder
├── data/                   # Mixed raw + pipeline outputs (legacy; being cleaned up)
│   ├── Convert to xcel sheet/   # Voter roll XLSX exports from PDF pipeline
│   ├── Outputs of pipline/      # DDP pipeline JSON/JSONL outputs
│   └── text/               # Affidavit text, MLA JSON, candidate JSON
├── transformed/            # Clean pipeline outputs ready for DB load
│   ├── 2022/
│   └── 2025/
├── seeds/                  # Static reference files (aliases, lexicons, villages)
│   ├── gorakhpur_aliases.json
│   ├── political_lexicon.json
│   └── unmatched_villages.json
└── labeled/                # Hand-labeled training examples for NLP classifiers
```

---

## Database Schema (PostgreSQL)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ac_master` | Assembly constituencies | `ac_id`, `ac_name`, `district_name` |
| `booth_master` | Polling stations | `booth_id`, `ac_id`, `booth_number`, `polling_station_name`, voter counts |
| `booth_results` | Election results per booth per year | `booth_id`, `election_year`, `party`, `votes`, `vote_share`, `winner_flag` |
| `candidate_master` | Candidate registry | `candidate_id`, `ac_id`, `name`, `party`, `is_incumbent` |
| `candidate_affidavits` | ECI affidavit details | `candidate_id`, `age`, `education`, `criminal_cases`, `total_assets` |
| `panchayat_master` | GP/block reference | `panchayat_id`, `gp_name`, `block_name`, `district_id` |
| `scheme_activity` | eGramSwaraj scheme execution | `panchayat_id`, `scheme_name`, `financial_year`, `gp_count` |
| `pulse_events` | NLP-tagged social/news signals | `booth_id`, `entity`, `final_polarity`, `final_issue`, `source_type` |
| `booth_metrics` | Pre-computed booth KPIs | `booth_id`, `bjp_pulse_score`, `opp_pulse_score`, `digital_lean_label` |
| `scheme_gap_analysis` | Scheme gap per booth | `booth_id`, `scheme_name`, `gap_type`, `priority`, `beneficiary_count` |
| `booth_narratives` | Narrative patterns detected | `booth_id`, `narrative_type`, `strength`, `evidence_count` |
| `contradiction_flags` | Cross-source conflicts | `booth_id`, `entity`, `source_a`, `source_b`, `delta` |
| `data_quality_metrics` | Quality scores per booth | `booth_id`, `overall_quality_score`, `quality_label`, `source_diversity_score` |
| `political_events` | Rally/protest/announcement events | `ac_id`, `event_type`, `event_date`, `parties_mentioned` |

---

## ETL Modules (`etl/`)

### `kruti_to_unicode.py` ✅ Complete
Converts KrutiDev 010 (legacy ANSI font) to Unicode Devanagari.  
- `kruti_to_unicode(text)` — single-char fast path + 2-char lookahead + pre-base i-matra reordering  
- Critical for: booth names in Form-20 XLS, which store Devanagari in KrutiDev encoding  
- **Remaining**: Full conjunct mapping for rare district variants (covers >90% of government form text)

### `parse_form20_xls.py` ✅ Complete
Parses ECI Form-20 XLS → `booth_master` + `booth_results`.  
- Reads `data/raw/2022/form20/*.xls`, skips 6 header rows  
- Applies `kruti_to_unicode` on polling station names  
- Inserts booth voter counts and per-candidate vote totals  
- Marks winners (max votes per booth)  
- **Run**: `python -m etl.parse_form20_xls`  
- **Status**: Script complete; needs re-run after DB is live to populate `booth_results`

### `transform_geography.py` ✅ Complete
Loads AC master + booth demographics from electoral roll XLSX.  
- `load_ac_master()` — seeds all 9 Gorakhpur ACs (GKP_320 to GKP_328)  
- `load_booth_master()` — reads voter roll XLSX, aggregates to booth-level M/F/Other counts  
- Connector key: `booth_id = f"GKP_{ac_number}_{part:03d}"`

### `transform_candidates.py` ⚠️ Partial
Loads candidate data from JSON files into `candidate_master`.  
- Source: `data/data/text/affidavit_gorakhpur_all_candidates.json` (name + party only, no financials)  
- **Gap**: Affidavit detail (age, assets, education) not in source JSON — use `seed_known_candidates.py` instead

### `seed_known_candidates.py` ✅ New
Seeds known public affidavit data for 3 key GKP_322 candidates (2022 + 2017).  
- Yogi Adityanath (BJP), Subhawati Shukla (SP), Khwaja Shamsuddin (BSP)  
- **Run**: `python -m etl.seed_known_candidates`

### `transform_schemes.py` ✅ Complete (FK fix applied)
Loads eGramSwaraj scheme data → `panchayat_master` + `scheme_activity`.  
- `load_block_wise_summary()` — block aggregates, self-heals panchayat FK  
- `load_district_expenditure()` — district totals, self-heals `GKP_DISTRICT_AGGREGATE` FK  
- **Gap**: `beneficiary_count` = 0 for most rows (source has GP count, not household count)

### `transform_panchayats.py` ✅ Complete
Seeds panchayat reference rows from JSON/CSV.

### `ingest_youtube_videos.py` ✅ New
Loads 831 videos from `data/Digital_Dataset/Youtube/videos/metadata/video_index.json` into:
- `yt_channels` — deduplicated channel rows
- `yt_videos` — one row per video with metadata
- `pulse_events_raw` — one NLP-ready entry per video title + description (processed = FALSE)
- **Run**: `python -m etl.ingest_youtube_videos`
- Called automatically by `flow_load_graph.py --stage etl`

### `transform_census.py` ⚠️ Partial
Loads demographic census data. Booth-level census linkage incomplete.

### `transform_news.py` ⚠️ Partial
Transforms scraped news into `pulse_events`. Needs NLP pipeline run first.

### `load_gorakhpur_baseline.py` ✅ Complete
One-shot baseline loader — calls all `transform_*` modules in dependency order.  
**Run order**: `python -m etl.load_gorakhpur_baseline`

### `load_real_schemes.py` ✅ Complete
Alternative scheme loader using direct eGramSwaraj CSV exports.

### `ingest_eroll_data.py` ⚠️ Partial
Ingests electoral roll XLSX + pipeline JSONL into booth_master demographics.  
- `data/data/Outputs of pipline/eroll_322_part2/electoral_roll_records_english.jsonl` has `part_no: null` — booth mapping not possible without DDP pipeline fix.

### `compute_booth_metrics.py` ✅ Complete
Pre-computes `booth_metrics` (pulse scores, lean labels, top issues) from `pulse_events`.  
**Run**: `python -m etl.compute_booth_metrics`

### `pulse_event_prep.py` ✅ Complete
Prepares raw text events for NLP pipeline, writes to `pulse_events` staging.

### `update_booth_results.py` ✅ Complete
Supplemental script to update `booth_results` vote shares after insert.

---

## Ingestion Modules (`ingestion/`)

| Module | Source | Status |
|--------|--------|--------|
| `eci_booth_results.py` | ECI website scraper | ⚠️ Needs auth/cookies |
| `eci_results_scraper.py` | Fallback scraper | ⚠️ Partial |
| `myneta_candidates.py` | MyNeta affidavit API | ⚠️ Rate limited |
| `ddp_affidavits.py` | DDP pipeline | ⚠️ Garbled binary output |
| `ddp_electoral_roll.py` | DDP pipeline | ⚠️ `part_no: null` in output |
| `egramswaraj_schemes.py` | eGramSwaraj API | ✅ Working |
| `youtube_comments.py` | YouTube Data API v3 | ✅ Working |
| `news_scraper.py` | RSS + scraping | ✅ Working |
| `mla_works.py` | NEVA MLA works portal | ✅ Working |
| `electoral_demographics.py` | Voter roll demographics | ✅ Working |

---

## Analytics Modules (`analytics/`)

### `booth_metrics.py` ✅ Complete
Computes BJP/Opp pulse scores, digital lean labels, confidence scores per booth.

### `scheme_gap_analysis.py` ✅ Complete
Classifies each scheme as execution_gap / reach_gap / performing_well / etc.  
- **Gap**: `beneficiary_count` relies on eGramSwaraj data which has GP counts, not households.  
- **Workaround**: Multiply `gp_count × ~250` to estimate household reach.

### `narrative_detector.py` ✅ Complete
Detects narrative patterns (anti-incumbency, development, welfare, etc.) across booths.

### `contradiction_detector.py` ✅ Complete
Flags entities where YouTube vs. news signals conflict (MIXED_SIGNALS).

### `data_quality.py` ✅ Complete
Computes per-booth data quality scores (source diversity, geo confidence, entity match rate).

### `historical_analysis.py` ✅ Complete
Derives historical vote trends from `booth_results` for booth-level BJP trajectory.

---

## API Modules (`api/`)

### `main.py` ✅ Complete — 16 endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness check |
| `GET /ac/{ac_id}/booths` | All booths with pulse scores |
| `GET /ac/{ac_id}/candidates` | Candidate list with affidavits |
| `GET /ac/{ac_id}/schemes` | Aggregated scheme gap analysis |
| `GET /ac/{ac_id}/narratives` | AC-level narrative trends |
| `GET /ac/{ac_id}/events` | Political events timeline |
| `GET /ac/{ac_id}/quality` | AC-level data quality summary |
| `GET /ac/{ac_id}/recommendations` | Strategic risks + action items |
| `GET /booth/{booth_id}/summary` | Full booth intelligence card |
| `GET /booth/{booth_id}/pulse` | Pulse time-series |
| `GET /booth/{booth_id}/issues` | Top issues by mention count |
| `GET /booth/{booth_id}/comments` | Backing evidence comments |
| `GET /booth/{booth_id}/quality` | Per-booth quality metrics |
| `GET /booth/{booth_id}/narratives` | Narrative patterns for booth |
| `GET /booth/{booth_id}/contradictions` | Cross-source conflicts |
| `GET /graph/subgraph` | Neo4j 1-hop subgraph |

### `queries.py` ✅ Complete
All SQL queries. Uses `LATERAL JOIN` for latest-row lookups, `MODE() WITHIN GROUP` for AC aggregates.

### `db.py` ✅ Complete
Connection factories for PostgreSQL (`get_pg_engine`) and Neo4j (`get_neo4j_session`).

---

## Dashboard Pages (`dashboard/pages/`)

| Page | File | Status | Data Source |
|------|------|--------|-------------|
| Constituency Overview | `ac_overview.py` | ✅ | `/ac/{id}/booths` |
| Booth Intelligence | `booth_summary.py` | ✅ | `/booth/{id}/summary` |
| Candidate Intelligence | `candidate_panel.py` | ✅ | `/ac/{id}/candidates` + known seed |
| Scheme Intelligence | `scheme_intelligence.py` | ✅ | `/ac/{id}/schemes` |
| Narrative & Sentiment | `narrative_sentiment.py` | ✅ | `/ac/{id}/narratives` |
| Event Timeline | `event_timeline.py` | ✅ | `/ac/{id}/events` |
| Knowledge Graph | `knowledge_graph.py` | ✅ | `/graph/subgraph` |
| Data Quality | `data_quality.py` | ✅ | `/ac/{id}/quality` |
| Recommendations | `recommendations.py` | ✅ | `/ac/{id}/recommendations` |

All pages include realistic demo fallbacks when live data is absent.  
**Run**: `streamlit run dashboard/app.py`

---

## Graph Modules (`graph/`, `flows/graph/`)

| File | Purpose | Status |
|------|---------|--------|
| `graph/loaders/load_candidates.py` | Loads candidates into Neo4j | ✅ |
| `graph/loaders/load_youtube.py` | Loads YouTubeVideo + Channel nodes into Neo4j | ✅ |
| `graph/loaders/load_mla_works.py` | Loads MLA works into Neo4j | ✅ |
| `graph/constraints.cypher` | Neo4j uniqueness constraints | ✅ |
| `flows/graph/flow_load_graph.py` | Orchestrates full graph load | ✅ |
| `graph/queries/cypher_lib.py` | Reusable Cypher queries | ✅ |

Neo4j node types: `AC`, `Booth`, `Candidate`, `Party`, `Issue`, `Scheme`, `Panchayat`

---

## NLP Modules (`nlp/`)

| Module | Purpose | Status |
|--------|---------|--------|
| `pipeline.py` | Main NLP processing pipeline | ✅ |
| `extractor.py` | Entity + issue extraction | ✅ |
| `geo_resolver.py` | Text → booth/AC mapping | ✅ |
| `rule_classifier.py` | Rule-based issue/polarity classifier | ✅ |
| `lang_detect.py` | Hindi/English detection | ✅ |
| `bhashini.py` | Bhashini API translation wrapper | ⚠️ API key needed |
| `alias_expander.py` | Expands location/candidate aliases | ✅ |

---

## Flows / Orchestration (`flows/`)

| Flow | Purpose | Status |
|------|---------|--------|
| `flows/graph/flow_load_graph.py` | Full ETL → Neo4j graph load | ✅ |
| `flows/aggregation/` | Aggregation flows | ⚠️ Partial |
| `flows/dynamic_signals/` | Real-time signal processing | ⚠️ Partial |
| `flows/nlp/` | Batch NLP pipeline flow | ✅ |

---

## Infrastructure

| File | Purpose |
|------|---------|
| `docker-compose.yml` | PostgreSQL + Neo4j + Redis |
| `.env` | DB URLs, API keys |
| `db/migrations/001_initial.sql` | Base schema |
| `db/migrations/002_quality_narratives.sql` | Quality + narrative tables |
| `db/migrations/003_new_tables.sql` | Events + recommendations tables |
| `db/seeds/seed_issues.sql` | Issue taxonomy seed |
| `.streamlit/config.toml` | War-room dark theme |

---

## What Is Done

- Full PostgreSQL schema (15 tables) with migrations ✅
- Neo4j graph with constraints and loaders ✅
- All 9 dashboard pages with war-room dark theme ✅
- FastAPI with 16 endpoints ✅
- ETL for geography, Form-20 results, schemes, panchayats ✅
- KrutiDev → Unicode converter (production-grade) ✅
- Analytics: pulse metrics, narratives, contradictions, data quality, scheme gaps ✅
- Demo fallbacks on every dashboard page ✅
- Candidate seed data for 3 key candidates ✅

## What Is Incomplete / Remaining Work

| Item | Gap | Fix |
|------|-----|-----|
| Booth names (Kruti Dev) | Re-run `parse_form20_xls.py` against live DB | `python -m etl.parse_form20_xls` |
| Candidate affidavit detail | Run seed script | `python -m etl.seed_known_candidates` |
| Scheme beneficiaries | eGramSwaraj has GP count, not household count | Multiply `gp_count × 250` or source PMAY/JJM beneficiary lists |
| Electoral roll booth mapping | DDP JSONL has `part_no: null` | Fix DDP pipeline to extract part header from PDF section titles |
| 2017 historical results | Form-20 for 2017 not yet parsed | Add 2017 XLS to `data/raw/2017/form20/` and re-run parser |
| YouTube + news live ingestion | Needs API keys in `.env` | Set `YOUTUBE_API_KEY`, `NEWS_API_KEY` |
| Bhashini translation | Needs API key | Set `BHASHINI_API_KEY` in `.env` |
| More ACs beyond GKP_322 | Only Gorakhpur Urban has Form-20 data | Obtain Form-20 XLS for GKP_320–328 |
| MyNeta affidavit scraper | Rate limited | Schedule with delay or use static seed |
| Census → booth linkage | Village-to-booth mapping 60% complete | Extend `geo_resolver.py` village aliases |

---

## Run Order (Fresh Setup)

```bash
# 1. Infrastructure
docker compose up -d

# 2. Migrations
psql $POSTGRES_URL < db/migrations/001_initial.sql
psql $POSTGRES_URL < db/migrations/002_quality_narratives.sql
psql $POSTGRES_URL < db/migrations/003_new_tables.sql
psql $POSTGRES_URL < db/seeds/seed_issues.sql

# 3. ETL
psql $POSTGRES_URL -f db/migrations/004_fixes.sql   # unique constraints + yt_videos cols
python -m etl.load_gorakhpur_baseline      # geography + panchayats + schemes
python -m etl.parse_form20_xls             # booth results from Form-20
python -m etl.seed_known_candidates        # candidate affidavits
python -m etl.ingest_youtube_videos        # 831 YT videos → yt_videos + pulse_events_raw

# 4. Analytics
python -m analytics.scheme_gap_analysis
python -m etl.compute_booth_metrics

# 5. Graph
python -m flows.graph.flow_load_graph --stage etl

# 6. API + Dashboard
uvicorn api.main:app --reload &
streamlit run dashboard/app.py
```
