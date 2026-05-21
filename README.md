# Gorakhpur Booth Knowledge Graph & Sentiment Engine

🎯 **Mission: Win Elections Through Hyper-Local Intelligence**
UP-Election-Ontology-Engine is a booth-level political intelligence platform designed to help political parties win elections through data-driven, hyper-local insights. By building a comprehensive ontology of voter demographics, local governance, public sentiment, and historical voting patterns, this engine enables precise micro-targeting and strategic decision-making at the booth level.

> Booth-level political intelligence for Gorakhpur Urban, Uttar Pradesh.
> Maps election geography → ingests digital signals → runs multilingual sentiment → delivers analyst dashboard.

---

## What This Builds

```
Booth 223 (Gorakhpur Urban)
├── 🗳️  Historical: BJP won last 2 elections | Vote share: 55% → 48% (declining)
├── 📊  Digital Lean: Lean BJP
├── ⚠️   Data Quality: MEDIUM — Only YouTube data (78%) | 28% AC-level mapping
├── 🔥  Top Issues: Water ↑+22%  |  Jobs ↑+10%
├── 🏛️  Candidate Insights: BJP +ve on development, -ve on water
├── 📉  Scheme Gap: PMAY → reach_gap (low beneficiaries + complaints high)
├── 🧩  Dominant Narrative: anti_incumbency (strength 0.62)
├── ⚡  Mixed Signal: BJP — YouTube +0.4 vs News -0.3 (SWING_INDICATOR)
├── 🧠  Key Insight: Strong base, growing dissatisfaction on water
└── 📌  Recommendation: Focus campaign on water + jobs
```

Every field above is backed by real data — ECI booths, MyNeta affidavits,
eGramSwaraj schemes, YouTube comments, local news — all flowing through a
deterministic multilingual (Hindi/Bhojpuri/English) NLP pipeline into a
Neo4j knowledge graph with 5 intelligence layers.

---

## ⚡ What This Engine Does (Core Capabilities)

*   **Booth-Level Geography Mapping:** Maps complete election geography (State → District → AC → Booth → Panchayat → Village). Integrates official ECI booth master data with local boundaries.
*   **Voter Knowledge Graph:** Builds a living Neo4j graph capturing demographics and linking voters to local schemes. Privacy-first: No PII stored.
*   **Real-Time Sentiment & Pulse Analysis:** Continuously ingests digital signals via a multilingual NLP pipeline to compute booth-level pulse scores and track sentiment trends.
*   **Candidate & Party Profiling:** Integrates candidate affidavits and historical election performance mapping.
*   **Governance Intelligence:** Aggregates panchayat development activities, maps scheme delivery, and identifies governance gaps vs. public sentiment.
*   **Hyper-Local Voter Segmentation:** Segments voters to generate booth-specific messaging recommendations.

---

## 📊 Key Use Cases

1.  **Pre-Election Assessment:** Analyze current sentiment and historical patterns to generate a booth risk/opportunity matrix.
2.  **Campaign Planning:** Identify high-priority booths (swing, fence-sitter) and track scheme delivery vs. public perception to output a campaign playbook.
3.  **Real-Time Campaign Monitoring:** Track sentiment shifts daily, monitor competitor messaging, and identify emerging local issues.
4.  **Post-Election Analysis:** Analyze voting patterns vs. pre-election predictions to understand what messaging worked in which booths.

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
└──────────────────────────────────────────────────────────────────────┘
                              │  nlp/pipeline.py
                              │  lang_detect → bhashini → groq+instructor → geo_resolve
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
│  FASTAPI   /ac/{id}/booths  /booth/{id}/summary  /booth/{id}/pulse  │
│            /booth/{id}/quality  /booth/{id}/narratives               │
│            /booth/{id}/contradictions  /ac/{id}/candidates           │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  STREAMLIT DASHBOARD  — Booth 223 card with all 10 intelligence panels│
└──────────────────────────────────────────────────────────────────────┘
```

---

## Neo4j Graph Schema

### Core nodes

| Node | Key property | Description |
|------|-------------|-------------|
| `State` | `name` | Uttar Pradesh |
| `District` | `name` | Gorakhpur |
| `AssemblyConstituency` | `ac_id` | e.g. `GKP_URBAN` |
| `Booth` | `booth_id` | e.g. `GKP_U_045` |
| `Candidate` | `candidate_id` | MyNeta affidavit data |
| `Party` | `name` | BJP, SP, BSP, Congress |
| `Issue` | `code` | water, roads, jobs, corruption … |
| `Scheme` | `name` | PMAY, Ujjwala, MGNREGA … |
| `Panchayat` | `panchayat_id` | eGramSwaraj unit |
| `PulseEvent` | `event_id` | Single sentiment extraction |
| `Election` | `election_id` | 2017, 2022 results |

### Intelligence layer nodes

| Node | Key properties | Wires to |
|------|---------------|----------|
| `DataQuality` | `booth_id`, `computed_at`, `quality_label`, `overall_quality_score`, `quality_reasons[]` | `Booth` via `HAS_QUALITY` |
| `Narrative` | `booth_id`, `narrative_type`, `strength`, `description` | `Booth` via `HAS_NARRATIVE`; `Issue` via `ABOUT_ISSUE`; `Party/Candidate` via `INVOLVES_PARTY/INVOLVES_CANDIDATE` |
| `SchemeGap` | `booth_id`, `scheme_name`, `gap_type`, `gap_label`, `priority` | `Booth` via `HAS_SCHEME_GAP`; `Scheme` via `FOR_SCHEME`; `Issue` via `TAGGED_ISSUE` |
| `ContradictionFlag` | `booth_id`, `entity`, `source_a/b`, `delta`, `flag_label` | `Booth` via `HAS_CONTRADICTION`; `Party/Candidate` via `ABOUT_ENTITY` |

### Relationship types

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

## 5 Intelligence Layers

| Layer | File | What it detects | Output |
|-------|------|----------------|--------|
| 1. Data Quality | `analytics/data_quality.py` | Source bias, geo resolution gaps, NLP confidence | `data_quality_metrics` + `DataQuality` node |
| 2. Scheme Gap | `analytics/scheme_gap_analysis.py` | execution_gap / reach_gap / awareness_gap / performing_well | `scheme_gap_analysis` + `SchemeGap` node |
| 3. Alias Expansion | `nlp/alias_expander.py` | Unmatched location mentions → auto-proposes new aliases | Updates `gorakhpur_aliases.json` |
| 4. Contradiction Detection | `analytics/contradiction_detector.py` | YouTube vs News polarity divergence per entity | `contradiction_flags` + `ContradictionFlag` node |
| 5. Narrative Detection | `analytics/narrative_detector.py` | anti_incumbency / development / corruption / swing patterns | `booth_narratives` + `Narrative` node |

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

## Repo Structure

```
gorakhpur-kg/
├── data/seeds/
│   ├── gorakhpur_aliases.json        ← locality → booth_id (auto-expanded by alias_expander)
│   └── political_lexicon.json
│
├── ingestion/                   ← scrapers, one file per source
│   ├── eci_booths.py
│   ├── myneta_candidates.py
│   ├── eci_booth_results.py
│   ├── egramswaraj_schemes.py
│   ├── youtube_comments.py
│   └── news_scraper.py
│
├── etl/
│   ├── booth_panchayat_join.py
│   └── pulse_event_prep.py
│
├── nlp/                         ← 7-stage multilingual pipeline
│   ├── schemas.py
│   ├── lang_detect.py
│   ├── bhashini.py
│   ├── extractor.py
│   ├── rule_classifier.py
│   ├── geo_resolver.py
│   ├── alias_expander.py        ← Fix 3: dynamic alias learning
│   └── pipeline.py
│
├── graph/
│   ├── constraints.cypher       ← core node constraints
│   ├── constraints_v2.cypher    ← intelligence layer constraints
│   ├── loaders/
│   │   ├── load_structure.py
│   │   ├── load_booths.py
│   │   ├── load_candidates.py
│   │   ├── load_panchayats.py
│   │   ├── load_pulse_events.py
│   │   └── load_quality_narratives.py  ← DataQuality/Narrative/SchemeGap/Contradiction → Neo4j
│   └── queries/
│       └── cypher_lib.py        ← all Cypher queries used by API
│
├── analytics/
│   ├── booth_metrics.py
│   ├── data_quality.py          ← Fix 1: multi-dimensional quality scoring
│   ├── scheme_gap_analysis.py   ← Fix 2: 4-way gap classification
│   ├── contradiction_detector.py ← Fix 4: cross-source signal conflicts
│   ├── narrative_detector.py    ← Fix 5: narrative pattern detection
│   └── historical_analysis.py
│
├── api/
│   ├── main.py                  ← 9 endpoints (+ 3 new: quality/narratives/contradictions)
│   ├── db.py
│   ├── queries.py
│   └── schemas.py
│
├── dashboard/
│   ├── app.py
│   └── pages/
│       ├── booth_summary.py     ← 10-panel card
│       ├── candidate_panel.py
│       ├── evidence_feed.py
│       └── ac_overview.py
│
├── flows/
│   ├── nlp/flow_sentiment.py
│   ├── graph/flow_load_graph.py
│   └── aggregation/
│       ├── flow_booth_metrics.py
│       └── flow_full_analytics.py  ← orchestrates all 5 intelligence layers
│
├── db/migrations/
│   ├── 001_initial.sql          ← 14 core tables
│   └── 002_quality_narratives.sql  ← 4 intelligence tables + booth_metrics columns
│
├── tests/
│   ├── unit/
│   │   ├── test_sentiment.py
│   │   └── test_geo_resolver.py
│   └── integration/test_pipeline.py
│
├── .env.example
├── requirements.txt
├── docker-compose.yml
└── pyproject.toml
```

---

## Key Metrics per Booth

| Metric | Formula | Source |
|--------|---------|--------|
| BJP Pulse Score | `Σ(polarity × confidence × source_weight) / Σ(weights)` | pulse_events |
| Opposition Pulse | Same for SP/BSP/Congress | pulse_events |
| Digital Lean | `bjp_pulse - opp_pulse` | computed |
| Top Issues | Weighted issue count, ranked | pulse_events |
| Issue Momentum | `(last_7d_count - prev_7d_count) / prev_7d_count` | pulse_events |
| Data Quality Score | `0.25×volume + 0.25×geo + 0.30×nlp + 0.20×diversity` | data_quality_metrics |
| Scheme Gap Type | 4-way classification (execution/reach/awareness/well) | scheme_gap_analysis |
| Consistency Score | `1 - |polarity_a - polarity_b| / 2` | contradiction_flags |
| Narrative Strength | Weighted issue/party signal share | booth_narratives |
| Historical Trend | Vote share delta across elections | booth_results |

Source weights: survey=1.0 · field_note=0.9 · youtube=0.6 · news=0.4

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

---

## FastAPI Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ac/{ac_id}/booths` | All booths + pulse scores for AC |
| GET | `/booth/{id}/summary` | Full 10-panel Booth 223 card |
| GET | `/booth/{id}/pulse` | Pulse time-series |
| GET | `/booth/{id}/issues` | Top issues with polarity |
| GET | `/booth/{id}/comments` | Backing evidence feed |
| GET | `/booth/{id}/quality` | Data quality metrics + reasons |
| GET | `/booth/{id}/narratives` | Detected narrative patterns |
| GET | `/booth/{id}/contradictions` | Cross-source signal conflicts |
| GET | `/ac/{ac_id}/candidates` | Candidate affidavits + sentiment |

---

## Quickstart

### 1. Clone & environment

```bash
git clone git@github.com:Aryan-en/UP-ELection-Ontology-Engine.git
cd UP-ELection-Ontology-Engine
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # fill in your API keys
```

For AI reasoning, set `SARVAM_API_KEY` in `.env`. The backend will use Sarvam chat models first and fall back to Gemini if the Sarvam key is not present.

### 2. Start local infrastructure

```bash
docker-compose up -d
# Postgres on :5432, Neo4j on :7474/:7687, Redis on :6379
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

### 7. Start API + Dashboard

```bash
uvicorn api.main:app --reload --port 8000   # http://localhost:8000/docs
streamlit run dashboard/app.py              # http://localhost:8501
```

---

## Data Sources

| Source | What | Priority | Script |
|--------|------|----------|--------|
| CEO UP / ECI | Booth master, AC list | P0 | `ingestion/eci_booths.py` |
| MyNeta / ADR | Candidate affidavits | P0 | `ingestion/myneta_candidates.py` |
| ECI Results Archives | Historical booth results | P1 | `ingestion/eci_booth_results.py` |
| eGramSwaraj | Panchayat scheme delivery | P1 | `ingestion/egramswaraj_schemes.py` |
| YouTube (yt-dlp) | Comments on political videos | P1 | `ingestion/youtube_comments.py` |
| Jagran / Amar Ujala | Local news articles | P1 | `ingestion/news_scraper.py` |
| KoBoToolbox (Week 2) | Field surveys | P2 | manual → ETL |
| MGNREGA / PMAY (Week 2) | Beneficiary data | P2 | manual → ETL |

---

## 🗳️ Election Completeness & Null Policies

To support both complete historical datasets (like the 2017/2022 Vidhan Sabha results) and partially available datasets (like the 2024 Lok Sabha results), the engine implements a strict, PostgreSQL-first **Election Completeness and Null Policy**:

### 1. Database Completeness Taxonomy
Each row in the candidate results fact table (`candidate_party_history`) is annotated with a `result_completeness_status` state:
- `'complete'`: All contesting candidates have confirmed vote totals and ranks.
- `'winner_runnerup_only'`: Only the winner (rank 1) and runner-up (rank 2) have vote counts. All other non-winning candidates have `NULL` votes.
- `'partial'`: Used for temporal stubs or elections where vote totals are not yet seeded.

### 2. Strict Null Rules
- **Missing Votes**: All unconfirmed candidate vote counts remain `NULL` rather than being padded with zeros or runtime mocks.
- **Derived Metrics**: Any derived metrics (e.g., margins, vote share percentages) that depend on missing vote counts remain `NULL` to prevent mathematical distortion.
- **Uniqueness & key grain**: API and UI results are strictly queried using a unique grain key (`candidate_id + election_year + constituency_id + election_type`), removing slow and fragile runtime `GROUP BY` logic.

### 3. Neo4j Projections
The Neo4j graph loaders (`graph.loaders.load_candidates` and `load_results`) dynamically project the completeness status, campaign expenses, and voter metadata onto Candidate nodes and the `ELECTION_RESULT` relationship, ensuring graph visualizations are aligned with the operational database.

### 4. QA Audits
Continuous database integrity is enforced by `scripts/verify_election_results_qa.py` which validates:
- **Winner Uniqueness**: Maximum of one winner per constituency-year.
- **Monotonic Vote Ordering**: Winners have more votes than runners-up, descending down the ranks.
- **Null Policy Adherence**: Strictly checks that nulls are only allowed in matching completeness states.

---

## 🔐 Security & Compliance

*   **Electoral Roll Privacy:** No PII stored; only aggregated demographic counts.
*   **Data Encryption:** All sensitive data encrypted at rest and in transit.
*   **Access Control:** Role-based permissions (admin, analyst, campaign manager).
*   **Audit Trail:** Full versioning of data updates and user actions.
*   **Legal Compliance:** Designed within RPA 1951 election law constraints.

---

## Tech Stack

| Layer | Technology | Free Tier |
|-------|-----------|-----------|
| Relational DB | PostgreSQL 16 | Neon.tech (10GB) |
| Graph DB | Neo4j 5 | AuraDB Free or local Docker |
| Cache | Redis 7 | Upstash (free) |
| Orchestration | Prefect 3 | Prefect Cloud (free tier) |
| LLM Extraction | Groq (llama-3.3-70b) | Free tier generous |
| Translation | Bhashini API | Free (govt API) |
| API | FastAPI | Railway.app free tier |
| Dashboard | Streamlit | Community Cloud (free) |

---

## Team (15 people, 5 pods)

| Pod | Members | Owns |
|-----|---------|------|
| Infra + Backbone | P2, P3, P15 | DB, scrapers, security |
| Dynamic Signals | P4, P5, P13 | YouTube, news, ETL, lexicon |
| NLP + Sentiment | P6, P7, P8, P14 | Full NLP pipeline + alias expander |
| Graph + Analytics | P9, P11 | Neo4j, all 5 intelligence layers |
| UI + API + PM | P1, P10, P12 | FastAPI, Streamlit, demo |

---

## 📈 Success Metrics

*   **Coverage:** Booth-level data for entire AC(s).
*   **Sentiment Accuracy:** NLP confidence > 85% on ground-truth validation.
*   **Data Freshness:** Daily sentiment pulse updates.
*   **Prediction Power:** Pre-election booth-level sentiment vs. actual results correlation > 0.75.

---

## 🗓️ Roadmap

*   **Phase 1 (Weeks 1–5):** Gorakhpur Urban AC (1 AC, ~300 booths) ✓ *Core engine*
*   **Phase 2:** Add Campierganj AC (2nd AC)
*   **Phase 3:** Scale to full Gorakhpur district (4+ ACs)
*   **Phase 4:** Expand to other UP districts
*   **Phase 5:** Real-time WhatsApp/SMS campaign delivery integration

---

## 🤝 Contributing

This is a closed-source strategic tool. Access is restricted to core team members and authorized party functionaries.

---

## 📞 Support & Documentation

| File | Purpose |
|------|---------|
| `gorakhpur-master-plan.md` | Full 5-week plan, all 15 roles, all data sources |
| `gorakhpur-5day-sprint.md` | 5-day demo sprint with all runnable code |
| `docs/setup.md` | Local environment setup |
| `docs/api-contract.md` | FastAPI endpoint specs |
| `docs/demo-script.md` | Demo walkthrough script |

*Questions? Reach out to the core team lead.*
*Built with 🚀 for winning elections through data-driven, hyper-local insights.*
