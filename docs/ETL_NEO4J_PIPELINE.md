# Gorakhpur Political Intelligence Engine — End-to-End ETL & Neo4j Pipeline

> **Engine Type:** Deterministic Political Intelligence & Strategy Engine
> **Scope:** Gorakhpur Urban AC (322) — Pilot, ~235 booths
> **Goal:** Convert raw government data, news, and digital signals into booth-level strategic political insights

---

## Table of Contents

1. [Project Vision & What We Are Building](#1-project-vision)
2. [Data Inventory — Every File, Its Purpose](#2-data-inventory)
3. [Master Data Flow Diagram](#3-master-data-flow)
4. [ETL Stage-by-Stage Pipeline](#4-etl-pipeline)
5. [Neo4j Schema — Nodes, Properties, Relationships](#5-neo4j-schema)
6. [File-to-Node Mapping Table](#6-file-to-node-mapping)
7. [The 3 Critical Connector Keys](#7-connector-keys)
8. [Scrapers Required](#8-scrapers-required)
9. [NLP Pipeline (Deterministic)](#9-nlp-pipeline)
10. [Intelligence Layers](#10-intelligence-layers)
11. [UI Data Connections](#11-ui-data-connections)
12. [Execution Order](#12-execution-order)
13. [Gap Analysis — What Is Still Missing](#13-gap-analysis)

---

## 1. Project Vision

We are building a **Deterministic Political Intelligence & Strategy Engine** — NOT an ML prediction system.

### What It Answers

| Question | Example Output |
|---|---|
| What is happening in Booth 223? | Water dissatisfaction + anti-incumbency rising |
| Why is it happening? | Jal Jeevan Mission reach gap, 120 water complaints |
| Which groups are affected? | Women (water), Youth (jobs) |
| What strategic action improves turnout? | Water grievance camps + youth employment outreach |

### What We Are NOT Building

```
NOT:  "BJP wins with 63%"
YES:  "Water dissatisfaction + youth frustration are weakening BJP in Booth 223"
```

### Master Flow

```
DATA SOURCES (files + scrapers)
       ↓
   EXTRACTION (ETL Stage 1)
       ↓
  TRANSFORMATION (add connector keys, aggregate, normalize)
       ↓
  POSTGRES STAGING (gorakhpur_db — 18 tables)
       ↓
  NLP PIPELINE (lang_detect → translate → extract → geo_resolve)
       ↓
  ANALYTICS (5 intelligence layers — deterministic rules)
       ↓
  NEO4J GRAPH (full property graph + intelligence nodes)
       ↓
  FASTAPI (9 endpoints)
       ↓
  STREAMLIT DASHBOARD (9 pages, booth-level intelligence)
```

---

## 2. Data Inventory

### 2A. Files in `data/processed/text/` (and `data/processed/`)

| # | File | Format | Status | Contains |
|---|------|--------|--------|----------|
| 1 | `eci_electoral_roll_gorakhpur.json` | JSON | Ready | 9 AC numbers/names, ECI constituency metadata, electoral roll download status |
| 2 | `ceoup_gorakhpur_electoral_data.json` | JSON | Ready | 235 polling stations for Gorakhpur Urban (AC 322), Form-20 availability info |
| 3 | `affidavit_gorakhpur_all_candidates.json` | JSON | Ready | 37 candidates Urban 2022, 38 Rural 2022, 53 LS 2024 — name, party, status per candidate |
| 4 | `neva_gorakhpur_mla_data.json` | JSON | Ready | Current MLA: Yogi Adityanath (BJP, Urban 322) + Bipin Singh (BJP, Rural 323) — name, party, email, phone |
| 5 | `egramswaraj_gorakhpur_panchayat_data.json` | JSON | Ready | 1,273 gram panchayats, 20 blocks, 15,843 elected reps, block-wise GP counts, pradhan names |
| 6 | `BlockWiseSummaryReport_2022-2023.xls` | XLS | Ready | MGNREGA block-wise scheme expenditure, beneficiaries, completion — FY 2022-23 |
| 7 | `BlockWiseSummaryReport_2024-2025.xls` | XLS | Ready | MGNREGA block-wise scheme expenditure, beneficiaries, completion — FY 2024-25 |
| 8 | `DistrictWiseExpenditureReport.xls` | XLS | Ready | District-level scheme spending totals across all blocks |
| 9 | `PCA_CDB_0957_F_Census.xls` | XLS | Ready | Panchayat Census Abstract for Gorakhpur (block 0957) — village population, SC/ST, literacy |
| 10 | `electoral_roll.xlsx` | XLSX | Ready | Voter-level data: `Seq No, Name, Father/Husband, House No, Age, Gender, Status, EPIC No, Part No` |
| 11 | `electoral_roll (1).xlsx` | XLSX | Ready | Same schema as above — additional part numbers |
| 12 | `results-20260508043736 (3).csv` | CSV | Ready | News articles: `URL, MobileURL, Date, Title` (Hindi + English, Gorakhpur region) |
| 13 | `affidavit_gorakhpur_all_candidates.json` (text/) | JSON | Ready | Duplicate in text/ folder |
| 14 | `affidavit_gorakhpur_urban_2022_page1-4.txt` | TXT | Ready | OCR text from affidavit PDFs — criminal records, asset declarations, education |
| 15 | `collection_summary_2026-05-07.json` | JSON | Metadata | Scraper run log — not loaded to graph |
| 16 | `supplementary_portals_data.json` | JSON | Reference | Portal metadata (SVEEP, BharatMaps, MyScheme) — not loaded to graph directly |
| 17 | Screenshots (browser_sessions/, recordings/) | PNG/WebP | Discard | Scraper session captures — not loaded |
| 18 | Affidavit PDFs (8 files) | PDF | Parse | Raw ECI affidavit documents — source for OCR text files |

### 2B. Files That Need to Be Scraped (Scrapers Required)

| # | Source | What to Scrape | Target Table | Script |
|---|--------|---------------|-------------|--------|
| S1 | CEO UP / ECI Form-20 | Booth-level vote counts per party (2022 + 2024) | `booth_results` | `ingestion/eci_booth_results.py` |
| S2 | YouTube (yt-dlp) | Comments on Gorakhpur political videos | `yt_comments` | `ingestion/youtube_comments.py` |
| S3 | Dainik Jagran / Amar Ujala | Local Gorakhpur news articles (last 90 days) | `news_articles` | `ingestion/news_scraper.py` |
| S4 | eGramSwaraj API | Scheme completion status per panchayat | `scheme_activity` | `ingestion/egramswaraj_schemes.py` |
| S5 | UP Grievance Portal (IGRS) | Civic complaints by category and area | `grievance_events` | `ingestion/grievance_scraper.py` (NEW) |
| S6 | MyNeta / ADR | Full candidate affidavit details (assets, criminal records) | `candidate_master` | `ingestion/myneta_candidates.py` |
| S7 | ECI Electoral Roll PDFs | Convert CAPTCHA-blocked PDFs to structured booth voter counts | `booth_demographics` | Manual download + `etl/parse_electoral_roll.py` |

---

## 3. Master Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  RAW DATA LAYER                                                               │
│                                                                               │
│  ALREADY HAVE:                          SCRAPE REQUIRED:                      │
│  ├─ eci_electoral_roll.json             ├─ ECI Form-20 (booth vote counts)    │
│  ├─ ceoup_gorakhpur_electoral_data.json ├─ YouTube comments                   │
│  ├─ affidavit_gorakhpur_all.json        ├─ Jagran / Amar Ujala news           │
│  ├─ neva_gorakhpur_mla_data.json        ├─ eGramSwaraj scheme status          │
│  ├─ egramswaraj_panchayat_data.json     ├─ IGRS grievance portal              │
│  ├─ BlockWiseSummaryReport_*.xls        └─ MyNeta full affidavits             │
│  ├─ DistrictWiseExpenditureReport.xls                                         │
│  ├─ PCA_CDB_0957_F_Census.xls                                                │
│  ├─ electoral_roll.xlsx (x2)                                                  │
│  ├─ results-*.csv (news articles)                                             │
│  └─ affidavit_*_page*.txt (OCR)                                               │
└─────────────────┬────────────────────────────────────────────────────────────┘
                  │
                  ▼  ETL STAGE 1: EXTRACT + TRANSFORM
┌──────────────────────────────────────────────────────────────────────────────┐
│  TRANSFORMATION LAYER  (etl/)                                                 │
│                                                                               │
│  transform_geography.py     → generates: state_id, district_id, ac_id        │
│  transform_candidates.py    → generates: candidate_id, party_id, election_id │
│  transform_panchayats.py    → generates: panchayat_id, block_id → ac_id map  │
│  transform_schemes.py       → generates: scheme_id, gap_type (4-way rule)    │
│  transform_voters.py        → aggregates: booth_id counts (NO PII)            │
│  transform_census.py        → maps: village → booth demographics              │
│  transform_news.py          → stages: raw articles for NLP                    │
│  transform_affidavit_ocr.py → extracts: criminal_cases, assets from txt      │
└─────────────────┬────────────────────────────────────────────────────────────┘
                  │
                  ▼  ETL STAGE 2: LOAD TO POSTGRES
┌──────────────────────────────────────────────────────────────────────────────┐
│  POSTGRES STAGING (gorakhpur_db)                                              │
│                                                                               │
│  CORE TABLES:                           INTELLIGENCE TABLES:                  │
│  ├─ ac_master                           ├─ data_quality_metrics               │
│  ├─ booth_master                        ├─ booth_narratives                   │
│  ├─ candidate_master                    ├─ contradiction_flags                │
│  ├─ booth_results                       ├─ scheme_gap_analysis                │
│  ├─ panchayat_master                    └─ booth_metrics                      │
│  ├─ scheme_activity                                                           │
│  ├─ booth_demographics                                                        │
│  ├─ news_articles                                                             │
│  ├─ yt_comments                                                               │
│  ├─ grievance_events  (new)                                                   │
│  └─ pulse_events  (post-NLP)                                                  │
└─────────────────┬────────────────────────────────────────────────────────────┘
                  │
                  ▼  NLP PIPELINE (for text sources)
┌──────────────────────────────────────────────────────────────────────────────┐
│  NLP PIPELINE  (nlp/)                                                         │
│                                                                               │
│  Input: news_articles + yt_comments + grievance_events                        │
│                                                                               │
│  Step 1: lang_detect    → "hi" / "en" / "bho" (Bhojpuri)                     │
│  Step 2: bhashini       → Hindi/Bhojpuri → English translation                │
│  Step 3: alias_expand   → "योगी" → BJP, "साइकिल" → SP                        │
│  Step 4: rule_classifier → deterministic issue/entity tagging                 │
│  Step 5: groq_extract   → polarity, emotion, intensity, segment (LLM)         │
│  Step 6: geo_resolver   → location_mention → booth_id (fuzzy match)           │
│  Step 7: pulse_event    → write to pulse_events table                         │
└─────────────────┬────────────────────────────────────────────────────────────┘
                  │
                  ▼  ANALYTICS: 5 INTELLIGENCE LAYERS
┌──────────────────────────────────────────────────────────────────────────────┐
│  ANALYTICS LAYER  (analytics/)                                                │
│                                                                               │
│  Layer 1: data_quality.py         → DataQuality nodes                         │
│  Layer 2: scheme_gap_analysis.py  → SchemeGap nodes (4-way classification)   │
│  Layer 3: alias_expander.py       → Updates gorakhpur_aliases.json           │
│  Layer 4: contradiction_detector.py → ContradictionFlag nodes                │
│  Layer 5: narrative_detector.py   → Narrative nodes (8 pattern types)        │
└─────────────────┬────────────────────────────────────────────────────────────┘
                  │
                  ▼  NEO4J GRAPH LOAD
┌──────────────────────────────────────────────────────────────────────────────┐
│  NEO4J GRAPH  (graph/loaders/)                                                │
│                                                                               │
│  load_structure.py          → State, District, AC, Booth + hierarchy          │
│  load_candidates.py         → Candidate, Party + CONTESTED_IN, REPRESENTS     │
│  load_panchayats.py         → Panchayat + LOCATED_IN_AC, HAS_PANCHAYAT       │
│  load_schemes.py            → Scheme + SchemeGap + FOR_SCHEME, TAGGED_ISSUE   │
│  load_pulse_events.py       → PulseEvent + AT_BOOTH, MENTIONS_PARTY           │
│  load_quality_narratives.py → DataQuality, Narrative, ContradictionFlag       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. ETL Pipeline — Stage by Stage

### Stage 1A — Geography (Foundation — Everything Depends On This)

**Input Files:**
- `eci_electoral_roll_gorakhpur.json`
- `ceoup_gorakhpur_electoral_data.json`
- `electoral_roll.xlsx` + `electoral_roll (1).xlsx`

**Script:** `etl/transform_geography.py`

```python
# Keys generated — MUST be consistent across ALL scripts
state_id    = "UP"
district_id = "GKP"
ac_id       = f"GKP_{ac_number}"           # e.g. "GKP_322"
booth_id    = f"GKP_{ac_number}_{part_no:03d}"  # e.g. "GKP_322_045"
```

**Column-level Transform:**

| Source Column | Source File | Transform | Output Column | Postgres Table |
|---|---|---|---|---|
| `number` (int) | eci_electoral_roll.json | `f"GKP_{number}"` | `ac_id` | `ac_master` |
| `name` (str) | eci_electoral_roll.json | as-is | `ac_name` | `ac_master` |
| hardcoded | — | `"GKP"` | `district_id` | `ac_master` |
| hardcoded | — | `"UP"` | `state_id` | `ac_master` |
| `ac_number` (int) | ceoup.json | `169` (for Urban 322) | `ac_number` | `booth_master` |
| `total_polling_stations` | ceoup.json | `235` | `total_booths` | `booth_master` |
| `sample_stations[]` | ceoup.json | enumerate → part_no | `booth_name` | `booth_master` |
| `Part No` (int) | electoral_roll.xlsx | `f"GKP_322_{part_no:03d}"` | `booth_id` | `booth_master` |
| `Gender` | electoral_roll.xlsx | groupby Part No, count M/F | `male_voters`, `female_voters` | `booth_demographics` |
| `Age` | electoral_roll.xlsx | groupby Part No, bin ages | `age_18_25`, `age_26_40`, `age_40_60`, `age_60_plus` | `booth_demographics` |
| `Status` | electoral_roll.xlsx | count Status=='Active' | `active_voters` | `booth_demographics` |
| **Name, EPIC No, Father** | electoral_roll.xlsx | **DROPPED — PII** | — | — |

**Postgres Tables Output:**
```sql
-- ac_master
(ac_id, ac_number, ac_name, district_id, state_id, total_booths, phase)

-- booth_master
(booth_id, booth_name, ac_id, part_no, latitude, longitude)

-- booth_demographics  [AGGREGATED — no PII]
(booth_id, total_voters, male_voters, female_voters, other_voters,
 active_voters, age_18_25, age_26_40, age_40_60, age_60_plus)
```

---

### Stage 1B — Candidates & Parties

**Input Files:**
- `affidavit_gorakhpur_all_candidates.json`
- `neva_gorakhpur_mla_data.json`
- `affidavit_gorakhpur_urban_2022_page1-4.txt` (OCR)

**Script:** `etl/transform_candidates.py`

**Column-level Transform:**

| Source Column | Source File | Transform | Output Column | Postgres Table |
|---|---|---|---|---|
| `name` (str) | affidavit.json | as-is | `candidate_name` | `candidate_master` |
| `party` (str) | affidavit.json | `slug(party)` → `"BJP"` | `party_id` | `candidate_master` |
| `party` (str) | affidavit.json | as-is | `party_name` | `candidate_master` |
| `status` (str) | affidavit.json | as-is (Accepted/Rejected) | `nomination_status` | `candidate_master` |
| `constituency` + `election` | affidavit.json | map name → `ac_id` | `ac_id` | `candidate_master` |
| `election` (str) | affidavit.json | `"UP_ASM_2022"` or `"LS_2024"` | `election_id` | `candidate_master` |
| `phase` (int) | affidavit.json | as-is | `election_phase` | `candidate_master` |
| `name` + `party` + `election` | affidavit.json | `slug(name_year)` | `candidate_id` ← **PK** | `candidate_master` |
| `designation` | neva.json | e.g. "Chief Minister" | `designation` | `candidate_master` |
| OCR page text | affidavit_*.txt | regex extract | `criminal_cases_count` | `candidate_master` |
| OCR page text | affidavit_*.txt | regex extract | `total_assets_inr` | `candidate_master` |
| `email`, `phone` | neva.json | **DROPPED — PII** | — | — |

**Key slug rules (CRITICAL — must match Neo4j):**
```python
party_id     = party_name.strip().upper().split("(")[0].strip().replace(" ", "_")
# "Bharatiya Janata Party (BJP)" → "BJP"
# "Samajwadi Party (SP)"        → "SP"
# "Bahujan Samaj Party (BSP)"   → "BSP"

candidate_id = f"{name.upper().replace(' ','_')}_{election_year}"
# "ADITYANATH_2022"

ac_name_to_id = {
    "Gorakhpur Urban (322)": "GKP_322",
    "Gorakhpur Rural (323)": "GKP_323",
    "Caimpiyarganj (320)":   "GKP_320",
    # ... all 9 ACs
}
```

**Postgres Tables Output:**
```sql
-- candidate_master
(candidate_id, candidate_name, party_id, party_name, ac_id, election_id,
 election_phase, nomination_status, designation, criminal_cases_count, total_assets_inr)

-- party_master  [derived]
(party_id, party_name, party_abbrev, party_color)
```

---

### Stage 1C — Panchayats

**Input File:** `egramswaraj_gorakhpur_panchayat_data.json`

**Script:** `etl/transform_panchayats.py`

**Column-level Transform:**

| Source Column | Transform | Output Column | Postgres Table |
|---|---|---|---|
| `block` + `name` | `slug(block+"_"+name)` | `panchayat_id` ← **PK** | `panchayat_master` |
| `name` (str) | as-is | `panchayat_name` | `panchayat_master` |
| `block` (str) | as-is | `block_name` | `panchayat_master` |
| `block` | `BLOCK_TO_AC_MAP[block]` | `ac_id` ← **FK** | `panchayat_master` |
| `pradhan` (str) | as-is | `pradhan_name` | `panchayat_master` |
| `elected_members[]` | `len(elected_members)` | `total_reps` | `panchayat_master` |
| district_overview `male_representatives` | proportional estimate | `male_reps` | `panchayat_master` |
| district_overview `female_representatives` | proportional estimate | `female_reps` | `panchayat_master` |
| `block_wise_gram_panchayats` | `{block: count}` | `gp_count_by_block` | `panchayat_master` |

**Block-to-AC Lookup (must be hardcoded):**
```python
BLOCK_TO_AC_MAP = {
    "Khorabar":     "GKP_322",  # Gorakhpur Urban
    "Sardarnagar":  "GKP_322",  # Gorakhpur Urban
    "Chargawan":    "GKP_322",  # Gorakhpur Urban
    "Campierganj":  "GKP_320",  # Caimpiyarganj
    "Pipraich":     "GKP_321",  # Pipraich
    "Sahjanawa":    "GKP_324",  # Sahajanwa
    "Khajni":       "GKP_325",  # Khajani
    "Barhalganj":   "GKP_326",  # Chauri-Chaura
    "Bansgaon":     "GKP_327",  # Bansgaon
    "Belghat":      "GKP_328",  # Chillupar
    # ... verify remaining 10 blocks
}
```

**Postgres Table Output:**
```sql
-- panchayat_master
(panchayat_id, panchayat_name, block_name, ac_id, district_id,
 pradhan_name, total_reps, male_reps, female_reps, gp_count_in_block)
```

---

### Stage 1D — Schemes & Expenditure

**Input Files:**
- `BlockWiseSummaryReport_2022-2023.xls`
- `BlockWiseSummaryReport_2024-2025.xls`
- `DistrictWiseExpenditureReport.xls`

**Script:** `etl/transform_schemes.py`
**Dependency:** `pip install xlrd==1.2.0` (required for `.xls` format)

**Expected Column Structure (MGNREGA Block Report):**
```
Block | Scheme | Sanctioned_Amount | Expenditure | Beneficiaries | Completion_Pct | FY
```

**Column-level Transform:**

| Source Column | Transform | Output Column | Postgres Table |
|---|---|---|---|
| `scheme_name` | `slug(scheme_name)` | `scheme_id` ← **PK** | `scheme_master` |
| `scheme_name` | as-is | `scheme_name` | `scheme_master` |
| `block_name` | `BLOCK_TO_AC_MAP[block]` | `ac_id` | `scheme_activity` |
| `block_name` | as-is | `block_name` | `scheme_activity` |
| `sanctioned_amount` | float | `sanctioned_amount_inr` | `scheme_activity` |
| `expenditure` | float | `expenditure_inr` | `scheme_activity` |
| `beneficiaries` | int | `beneficiary_count` | `scheme_activity` |
| `completion_pct` | float | `completion_pct` | `scheme_activity` |
| FY header | `"2022-23"` or `"2024-25"` | `fiscal_year` | `scheme_activity` |
| computed | **4-way rule (see below)** | `gap_type` | `scheme_gap_analysis` |

**Gap Type Determination Rule (deterministic):**
```python
def classify_gap(completion_pct, beneficiary_count, sentiment_score):
    if completion_pct < 100:
        return "in_progress"
    if beneficiary_count < LOW_THRESHOLD and sentiment_score < 0:
        return "reach_gap"          # Not reaching people
    if beneficiary_count >= HIGH_THRESHOLD and sentiment_score < 0:
        return "execution_gap"      # Reached but unhappy — quality problem
    if beneficiary_count >= HIGH_THRESHOLD and abs(sentiment_score) < 0.2:
        return "awareness_gap"      # Reached but no credit
    if sentiment_score > 0.2:
        return "performing_well"
    return "no_data"
```

**Postgres Tables Output:**
```sql
-- scheme_master
(scheme_id, scheme_name, ministry, scheme_type, central_or_state)

-- scheme_activity
(activity_id, scheme_id, ac_id, block_name, fiscal_year,
 sanctioned_amount_inr, expenditure_inr, beneficiary_count, completion_pct)

-- scheme_gap_analysis  [computed in analytics layer]
(gap_id, booth_id, scheme_id, gap_type, gap_label, priority,
 beneficiary_count, expenditure_inr, sentiment_score, computed_at)
```

---

### Stage 1E — News Articles (Pre-NLP Staging)

**Input File:** `results-20260508043736 (3).csv`

**Script:** `etl/transform_news.py`

**Column-level Transform:**

| Source Column | Transform | Output Column | Postgres Table |
|---|---|---|---|
| `URL` | as-is | `source_url` | `news_articles` |
| `MobileURL` | as-is (nullable) | `mobile_url` | `news_articles` |
| `Date` | `datetime.strptime(d, "%Y-%m-%d %H:%M:%S")` | `published_at` | `news_articles` |
| `Title` | as-is | `raw_text` | `news_articles` |
| `URL` domain | `extract_domain(url)` | `source_name` | `news_articles` |
| computed | `hash(url + date)[:16]` | `article_id` ← **PK** | `news_articles` |
| — | `"news"` | `source_type` | `news_articles` |
| — | `0.8` (news weight) | `source_weight` | `news_articles` |
| — | `False` | `nlp_processed` | `news_articles` |

**Domain → Source Name Map:**
```python
DOMAIN_TO_SOURCE = {
    "bhaskar.com":              "Dainik Bhaskar",
    "navbharattimes.indiatimes.com": "Navbharat Times",
    "timesofindia.indiatimes.com":  "Times of India",
    "aninews.in":               "ANI",
    "indianexpress.com":        "Indian Express",
    "khaskhabar.com":           "Khas Khabar",
}
```

**Postgres Table Output:**
```sql
-- news_articles
(article_id, source_url, mobile_url, published_at, raw_text,
 source_name, source_type, source_weight, nlp_processed)
```

---

### Stage 1F — Census Demographics

**Input File:** `PCA_CDB_0957_F_Census.xls`

**Script:** `etl/transform_census.py`

**Expected PCA Column Structure:**
```
Village_Name | Total_Population | Male_Pop | Female_Pop | SC_Population |
ST_Population | Literate_Total | Literate_Male | Literate_Female | HH_Count
```

**Column-level Transform:**

| Source Column | Transform | Output Column | Postgres Table |
|---|---|---|---|
| `Village_Name` | fuzzy match → `booth_id` via alias JSON | `booth_id` | `village_demographics` |
| `Total_Population` | int | `total_population` | `village_demographics` |
| `Male_Pop` / `Female_Pop` | int | `male_pop`, `female_pop` | `village_demographics` |
| `SC_Population` | int | `sc_population` | `village_demographics` |
| `ST_Population` | int | `st_population` | `village_demographics` |
| `Literate_Total` | int | `literate_count` | `village_demographics` |
| computed | `literate / total * 100` | `literacy_rate_pct` | `village_demographics` |
| `HH_Count` | int | `household_count` | `village_demographics` |

**Postgres Table Output:**
```sql
-- village_demographics
(village_id, village_name, booth_id, ac_id,
 total_population, male_pop, female_pop, sc_population, st_population,
 literate_count, literacy_rate_pct, household_count)
```

---

## 5. Neo4j Schema

### Core Node Definitions

```cypher
// State
CREATE (s:State {
  state_id:   "UP",
  name:       "Uttar Pradesh"
})

// District
CREATE (d:District {
  district_id: "GKP",
  name:        "Gorakhpur",
  state_id:    "UP"
})

// AssemblyConstituency
CREATE (ac:AssemblyConstituency {
  ac_id:      "GKP_322",          // PRIMARY KEY
  ac_number:  322,
  name:       "Gorakhpur Urban",
  phase:      6,
  district_id: "GKP"
})

// Booth
CREATE (b:Booth {
  booth_id:       "GKP_322_045",  // PRIMARY KEY
  name:           "Primary School Madhopur",
  ac_id:          "GKP_322",
  part_no:        45,
  total_voters:   1142,
  male_voters:    610,
  female_voters:  532,
  age_18_25:      205,
  age_26_40:      380,
  age_40_60:      420,
  age_60_plus:    137,
  active_voters:  1100
})

// Candidate
CREATE (c:Candidate {
  candidate_id:       "ADITYANATH_2022",  // PRIMARY KEY
  name:               "Adityanath",
  party_id:           "BJP",
  ac_id:              "GKP_322",
  election_id:        "UP_ASM_2022",
  nomination_status:  "Accepted",
  designation:        "Chief Minister, Uttar Pradesh",
  criminal_cases_count: 0,
  total_assets_inr:   15000000
})

// Party
CREATE (p:Party {
  party_id:    "BJP",             // PRIMARY KEY
  name:        "Bharatiya Janata Party",
  abbrev:      "BJP",
  color:       "#FF9933"
})

// Panchayat
CREATE (pan:Panchayat {
  panchayat_id:   "KHORABAR_ADDA_MOTEERAM",  // PRIMARY KEY
  name:           "Adda Moteeram",
  block_name:     "Khorabar",
  ac_id:          "GKP_322",
  pradhan_name:   "Raju",
  total_reps:     13,
  male_reps:      7,
  female_reps:    6
})

// Scheme
CREATE (sc:Scheme {
  scheme_id:  "MGNREGA",          // PRIMARY KEY
  name:       "MGNREGA",
  ministry:   "Rural Development",
  type:       "employment"
})

// Issue
CREATE (i:Issue {
  code:        "water",           // PRIMARY KEY
  label:       "Water / Jal Jeevan",
  category:    "infrastructure",
  aliases_hi:  ["पानी", "जल संकट", "water problem", "पेयजल"]
})

// PulseEvent
CREATE (pe:PulseEvent {
  event_id:       "abc123def456",  // PRIMARY KEY = hash(url+date)
  source_url:     "https://...",
  published_at:   datetime("2026-04-15T14:15:00"),
  raw_text:       "पानी की बहुत समस्या है",
  language:       "hi",
  translated_text:"Water problem is very serious",
  polarity:       -0.72,
  confidence:     0.88,
  emotion:        "anger",
  intensity:      0.8,
  source_type:    "news",
  source_weight:  0.8,
  booth_id:       "GKP_322_045",
  issue_codes:    ["water"],
  party_mentions: ["BJP"]
})

// Election
CREATE (el:Election {
  election_id:  "UP_ASM_2022",    // PRIMARY KEY
  year:         2022,
  type:         "assembly",
  state:        "UP",
  phase:        6
})
```

### Intelligence Layer Nodes

```cypher
// DataQuality
CREATE (dq:DataQuality {
  quality_id:           "DQ_GKP_322_045_2026Q2",  // PRIMARY KEY
  booth_id:             "GKP_322_045",
  computed_at:          datetime(),
  overall_quality_score: 0.62,
  quality_label:        "MEDIUM",
  volume_score:         0.7,
  geo_score:            0.5,
  nlp_score:            0.8,
  diversity_score:      0.4,
  quality_reasons:      ["Only YouTube (78%)", "28% AC-level mapping"],
  source_bias_flag:     true
})

// Narrative
CREATE (n:Narrative {
  narrative_id:    "NAR_GKP_322_045_ANTI_INC",  // PRIMARY KEY
  booth_id:        "GKP_322_045",
  narrative_type:  "anti_incumbency",
  strength:        0.62,
  description:     "Strong base, growing dissatisfaction on water",
  computed_at:     datetime(),
  evidence_count:  18
})

// SchemeGap
CREATE (sg:SchemeGap {
  gap_id:          "GAP_GKP_322_045_PMAY",  // PRIMARY KEY
  booth_id:        "GKP_322_045",
  scheme_id:       "PMAY",
  gap_type:        "reach_gap",
  gap_label:       "Low beneficiaries + complaints high",
  priority:        "HIGH",
  beneficiary_count: 45,
  expenditure_inr: 2500000,
  sentiment_score: -0.6,
  computed_at:     datetime()
})

// ContradictionFlag
CREATE (cf:ContradictionFlag {
  flag_id:      "CF_GKP_322_045_BJP",  // PRIMARY KEY
  booth_id:     "GKP_322_045",
  entity:       "BJP",
  source_a:     "youtube",
  polarity_a:   0.4,
  source_b:     "news",
  polarity_b:   -0.3,
  delta:        0.7,
  flag_label:   "SWING_INDICATOR",
  computed_at:  datetime()
})
```

### All Relationship Types

```cypher
// Geographic hierarchy
(State)    -[:HAS_DISTRICT]->          (District)
(District) -[:HAS_AC]->                (AssemblyConstituency)
(AC)       -[:HAS_BOOTH]->             (Booth)
(AC)       -[:HAS_PANCHAYAT]->         (Panchayat)

// Election outcomes
(Booth)    -[:HAD_RESULT {year:2022, bjp_votes:620, sp_votes:280, turnout_pct:72.1}]-> (Election)
(Candidate)-[:CONTESTED_IN]->          (AssemblyConstituency)
(Candidate)-[:REPRESENTS]->            (Party)

// Pulse (sentiment signals)
(PulseEvent)-[:AT_BOOTH]->             (Booth)
(PulseEvent)-[:MENTIONS_PARTY]->       (Party)
(PulseEvent)-[:TAGGED_ISSUE]->         (Issue)

// Intelligence layer connections
(Booth)    -[:HAS_QUALITY]->           (DataQuality)
(Booth)    -[:HAS_NARRATIVE]->         (Narrative)
(Booth)    -[:HAS_SCHEME_GAP]->        (SchemeGap)
(Booth)    -[:HAS_CONTRADICTION]->     (ContradictionFlag)

// Intelligence cross-links
(Narrative)-[:ABOUT_ISSUE]->           (Issue)
(Narrative)-[:INVOLVES_PARTY]->        (Party)
(Narrative)-[:INVOLVES_CANDIDATE]->    (Candidate)
(SchemeGap)-[:FOR_SCHEME]->            (Scheme)
(SchemeGap)-[:TAGGED_ISSUE]->          (Issue)
(ContradictionFlag)-[:ABOUT_ENTITY]->  (Party)

// Scheme delivery chain
(Scheme)   -[:DELIVERED_IN]->          (Panchayat)
(Panchayat)-[:LOCATED_IN_AC]->         (AssemblyConstituency)
```

---

## 6. File-to-Node Mapping Table

This is the single source of truth for every file → every Neo4j node.

| Data File | Neo4j Node Created | Key Property Set | Relationship Wired |
|---|---|---|---|
| `eci_electoral_roll_gorakhpur.json` | `State`, `District`, `AssemblyConstituency` | `state_id`, `district_id`, `ac_id` | `HAS_DISTRICT`, `HAS_AC` |
| `ceoup_gorakhpur_electoral_data.json` | `Booth` | `booth_id`, `booth_name`, `part_no` | `HAS_BOOTH` |
| `electoral_roll.xlsx` (x2) | Updates `Booth` properties | `total_voters`, `male_voters`, `female_voters`, `age_*` | — (property update only) |
| `affidavit_gorakhpur_all_candidates.json` | `Candidate`, `Party` | `candidate_id`, `party_id` | `CONTESTED_IN`, `REPRESENTS` |
| `neva_gorakhpur_mla_data.json` | Updates `Candidate` | `designation` | — (property update only) |
| `affidavit_*_page*.txt` (OCR) | Updates `Candidate` | `criminal_cases_count`, `total_assets_inr` | — (property update only) |
| `egramswaraj_gorakhpur_panchayat_data.json` | `Panchayat` | `panchayat_id`, `block_name`, `pradhan_name` | `LOCATED_IN_AC`, `HAS_PANCHAYAT` |
| `BlockWiseSummaryReport_*.xls` | `Scheme`, `SchemeGap` | `scheme_id`, `gap_id`, `gap_type` | `FOR_SCHEME`, `HAS_SCHEME_GAP`, `TAGGED_ISSUE` |
| `DistrictWiseExpenditureReport.xls` | Updates `Scheme` | `district_expenditure_inr` | — (property update only) |
| `PCA_CDB_0957_F_Census.xls` | Updates `Booth` | `total_population`, `sc_population`, `literacy_rate_pct` | — (property update only) |
| `results-*.csv` → NLP → | `PulseEvent` | `event_id`, `polarity`, `booth_id` | `AT_BOOTH`, `MENTIONS_PARTY`, `TAGGED_ISSUE` |
| Analytics: `data_quality.py` | `DataQuality` | `quality_id`, `quality_label`, `overall_quality_score` | `HAS_QUALITY` |
| Analytics: `narrative_detector.py` | `Narrative` | `narrative_id`, `narrative_type`, `strength` | `HAS_NARRATIVE`, `ABOUT_ISSUE`, `INVOLVES_PARTY` |
| Analytics: `scheme_gap_analysis.py` | `SchemeGap` | `gap_id`, `gap_type`, `priority` | `HAS_SCHEME_GAP`, `FOR_SCHEME` |
| Analytics: `contradiction_detector.py` | `ContradictionFlag` | `flag_id`, `flag_label`, `delta` | `HAS_CONTRADICTION`, `ABOUT_ENTITY` |
| Scraped: ECI Form-20 | `BoothResult` (edge property) | `bjp_votes`, `sp_votes`, `turnout_pct` | `HAD_RESULT` |
| Scraped: YouTube comments | `PulseEvent` | Same as news but `source_type="yt_comment"`, `source_weight=0.6` | `AT_BOOTH`, `MENTIONS_PARTY` |
| Scraped: IGRS grievances | `PulseEvent` (grievance subtype) | `source_type="grievance"`, `source_weight=1.0` | `AT_BOOTH`, `TAGGED_ISSUE` |

---

## 7. The 3 Critical Connector Keys

These three keys wire the entire graph together. They **must be generated identically** in every ETL script, every analytics script, and every graph loader.

```python
# ============================================================
#  CONNECTOR KEY RULES — copy exactly into every script
# ============================================================

def make_booth_id(ac_number: int, part_no: int) -> str:
    """GKP_322_045  — zero-padded to 3 digits"""
    return f"GKP_{ac_number}_{part_no:03d}"

def make_ac_id(ac_number: int) -> str:
    """GKP_322"""
    return f"GKP_{ac_number}"

def make_party_id(party_name: str) -> str:
    """
    "Bharatiya Janata Party (BJP)" → "BJP"
    "Samajwadi Party (SP)"         → "SP"
    """
    name = party_name.strip().upper()
    # Extract abbreviation from parentheses if present
    if "(" in name:
        abbrev = name[name.rfind("(")+1 : name.rfind(")")]
        if 2 <= len(abbrev) <= 6:
            return abbrev
    # Fallback: first word
    return name.split()[0][:10]

# ============================================================
#  VALIDATION — run at the end of every transform script
# ============================================================
def validate_connector_keys(df, key_col):
    nulls = df[key_col].isna().sum()
    if nulls > 0:
        raise ValueError(f"FATAL: {nulls} null values in connector key {key_col}")
    duplicates = df[key_col].duplicated().sum()
    print(f"[OK] {key_col}: {len(df)} rows, {duplicates} duplicates, 0 nulls")
```

**What breaks if keys are inconsistent:**
- `"GKP_322_45"` vs `"GKP_322_045"` → PulseEvent disconnected from Booth (orphan node)
- `"bjp"` vs `"BJP"` → duplicate Party nodes, no relationships between them
- `"GKP322"` vs `"GKP_322"` → Candidate disconnected from AC

---

## 8. Scrapers Required

### S1 — ECI Form-20 Booth Results (HIGHEST PRIORITY)

**What:** Booth-level vote counts per party for 2022 Assembly + 2024 Lok Sabha elections.
**Why:** Without this, `HAD_RESULT` relationships are empty and we can't show historical trends.
**Script:** `ingestion/eci_booth_results.py`

```python
# Target URL pattern:
# ceouttarpradesh.nic.in → Election Results → Assembly Election 2022 → Form-20
# Returns: Constituency 322, each polling station, party-wise votes

# Output columns needed:
{
    "booth_id":    "GKP_322_045",    # from Part No + AC number
    "election_id": "UP_ASM_2022",
    "bjp_votes":   620,
    "sp_votes":    280,
    "bsp_votes":   95,
    "inc_votes":   28,
    "nota_votes":  18,
    "total_votes": 1041,
    "total_voters": 1142,
    "turnout_pct": 91.2
}
```

---

### S2 — YouTube Comments

**What:** Comments on Gorakhpur-focused political video channels.
**Why:** Digital pulse — primary sentiment signal for BJP/SP/BSP.
**Script:** `ingestion/youtube_comments.py`

```python
# Channels to scrape:
CHANNELS = [
    "AIR News Gorakhpur",  # credibility: 0.9, lean: neutral
    "Prabhat Khabar",      # credibility: 0.7, lean: neutral
    "local Gorakhpur channels",
]

# Search queries (use aliases from gorakhpur_aliases.json):
QUERIES = [
    "गोरखपुर विधानसभा",
    "योगी गोरखपुर",
    "gorakhpur election 2022",
    "gorakhpur water problem",
]

# Output columns needed:
{
    "comment_id":    "YT_abc123",
    "video_id":      "xyz789",
    "channel_name":  "AIR News Gorakhpur",
    "published_at":  "2026-04-15T10:00:00",
    "raw_text":      "पानी की बहुत समस्या है",
    "like_count":    42,
    "reply_count":   3,
    "source_type":   "yt_comment",
    "source_weight": 0.6,
    "credibility_score": 0.9,
    "bias_score":    0.1,
    "nlp_processed": False
}
```

---

### S3 — News Scraper (Extend Existing CSV)

**What:** Additional articles from Jagran, Amar Ujala, local Gorakhpur portals.
**Why:** The CSV we have (103 articles) is thin. Need 500+ for meaningful signal.
**Script:** `ingestion/news_scraper.py`

```python
# Sources:
NEWS_SOURCES = [
    {"url": "https://www.jagran.com/uttar-pradesh/gorakhpur-city.html",
     "credibility": 0.8, "bias": 0.3},
    {"url": "https://www.amarujala.com/uttar-pradesh/gorakhpur",
     "credibility": 0.8, "bias": 0.2},
    {"url": "https://navbharattimes.indiatimes.com/state/uttar-pradesh/gorakhpur",
     "credibility": 0.75, "bias": 0.2},
]

# Output columns: same schema as news_articles table above
# Additional columns from full article body:
{
    "article_id":    "NEWS_abc123",
    "full_text":     "...",         # full article body (not just title)
    "author":        "...",
    "tags":          ["gorakhpur", "BJP", "water"],
}
```

---

### S4 — eGramSwaraj Scheme Status (Per Panchayat)

**What:** Actual scheme completion status, financial progress per GP.
**Why:** Needed to compute `SchemeGap` nodes — without this, gap type is `no_data`.
**Script:** `ingestion/egramswaraj_schemes.py`

```python
# API endpoint (public):
# https://egramswaraj.gov.in/reportAnnualPlanActivityReport.do
# District code: 0957 (Gorakhpur)

# Output columns needed:
{
    "panchayat_id":      "KHORABAR_ADDA_MOTEERAM",
    "scheme_id":         "MGNREGA",
    "fiscal_year":       "2024-25",
    "sanctioned_amount": 2500000,
    "expenditure":       1875000,
    "beneficiary_count": 145,
    "completion_pct":    75.0,
    "activity_status":   "in_progress"
}
```

---

### S5 — IGRS UP Grievance Portal (NEW — Critical for Pain Points)

**What:** Civic complaints filed by citizens in Gorakhpur — water, electricity, roads.
**Why:** Grievances = REAL dissatisfaction. This is the strongest signal for issue detection.
**Script:** `ingestion/grievance_scraper.py` (new script)

```python
# Source: igrs.up.gov.in (Integrated Grievance Redressal System)
# Filter: District=Gorakhpur, Category=Civic

# Output columns needed:
{
    "grievance_id":   "GRV_2026_001234",
    "category":       "water",           # water / roads / electricity / jobs
    "area_name":      "Rustampur",       # locality name → geo_resolve → booth_id
    "booth_id":       "GKP_322_045",     # after geo_resolve
    "filed_at":       "2026-04-10",
    "status":         "pending",
    "description":    "No water supply for 3 days",
    "source_type":    "grievance",
    "source_weight":  1.0               # highest weight — real complaints
}
```

---

### S6 — MyNeta / ADR Full Affidavits

**What:** Detailed affidavit data — criminal cases, assets, liabilities, education.
**Why:** Candidate intelligence page needs this for trust/credibility signals.
**Script:** `ingestion/myneta_candidates.py`

```python
# Source: myneta.info/upvid2022/
# Already partially done — need to extract criminal + asset detail

# Additional columns needed:
{
    "candidate_id":          "ADITYANATH_2022",
    "criminal_cases_total":  0,
    "criminal_cases_serious": 0,
    "total_assets_inr":      15000000,
    "liabilities_inr":       0,
    "education":             "LLB",
    "age":                   50,
    "profession":            "Politician"
}
```

---

## 9. NLP Pipeline (Deterministic)

The NLP pipeline processes text from 3 sources: news articles, YouTube comments, and grievances.

### Pipeline Steps

```
Raw text (Hindi / Bhojpuri / English / mixed)
  ↓
Step 1: lang_detect.py
  → language: "hi" / "en" / "bho" / "mixed"

  ↓
Step 2: bhashini.py  [only if language != "en"]
  → translated_text: English
  → fallback: IndicTrans2 local model

  ↓
Step 3: alias_expander.py  [DETERMINISTIC]
  → "योगी" → entity: BJP
  → "साइकिल" → entity: SP
  → "पानी" → issue: water
  → Uses gorakhpur_aliases.json

  ↓
Step 4: rule_classifier.py  [DETERMINISTIC — primary]
  → if any(word in text for word in WATER_WORDS): issue = "water"
  → if any(word in text for word in BJP_ALIASES): party = "BJP"
  → confidence = 1.0 (rule-based is certain)

  ↓
Step 5: groq_extractor.py  [LLM — secondary, only if confidence < 0.6]
  → polarity: -1.0 to +1.0
  → emotion: anger / fear / hope / frustration / satisfaction
  → intensity: 0.0 to 1.0
  → inferred_segment: youth / women / farmers / urban_poor / unknown
  → segment_confidence: if < 0.7 → segment = "unknown"

  ↓
Step 6: geo_resolver.py
  → location_mention: "रुस्तमपुर" → booth_id: "GKP_322_045"
  → fuzzy match against gorakhpur_aliases.json
  → if no match → alias_expander proposes new entry

  ↓
Step 7: write pulse_event
  → INSERT INTO pulse_events (all columns)
  → nlp_processed = True on source table
```

### Alias JSON Structure (gorakhpur_aliases.json)

```json
{
  "parties": {
    "BJP": ["bjp", "भाजपा", "कमल", "yogi", "योगी", "modi", "double engine", "भारतीय जनता"],
    "SP":  ["akhilesh", "साइकिल", "समाजवादी", "अखिलेश"],
    "BSP": ["mayawati", "बसपा", "हाथी", "बहुजन"],
    "INC": ["congress", "कांग्रेस", "rahul", "हाथ"]
  },
  "issues": {
    "water":       ["पानी", "जल संकट", "water problem", "पेयजल", "नल जल", "jal jeevan"],
    "jobs":        ["नौकरी", "रोजगार", "बेरोजगारी", "unemployment", "job", "भर्ती"],
    "roads":       ["सड़क", "road", "गड्ढे", "pothole", "highway"],
    "electricity": ["बिजली", "power cut", "अंधेरा", "load shedding"],
    "corruption":  ["भ्रष्टाचार", "corruption", "घूस", "bribe", "scam"]
  },
  "localities": {
    "GKP_322_045": ["रुस्तमपुर", "rustampur", "Rustampur ward"],
    "GKP_322_046": ["मदहोपुर", "madhopur", "Madhopur area"],
    "GKP_322_047": ["सूरजकुंड", "surajkund"]
  },
  "segments": {
    "youth":       ["युवा", "youth", "student", "छात्र", "नौजवान"],
    "women":       ["महिला", "women", "माता", "बहन", "sister"],
    "farmers":     ["किसान", "farmer", "agriculture", "खेती", "MSP"]
  }
}
```

---

## 10. Intelligence Layers

These five analytics scripts run **after** NLP, computing derived nodes from `pulse_events` + `scheme_activity` + `booth_demographics`.

### Layer 1 — Data Quality (`analytics/data_quality.py`)

```python
# Formula: overall = 0.25×volume + 0.25×geo + 0.30×nlp + 0.20×diversity
# 
# volume_score  = min(event_count / 100, 1.0)
# geo_score     = booth_resolved_events / total_events
# nlp_score     = avg(confidence) across events for this booth
# diversity_score = len(unique_sources) / 4  (max 4 source types)
#
# Output → DataQuality node + HAS_QUALITY edge from Booth

DataQuality {
  quality_label: "HIGH" if score > 0.7
                 "MEDIUM" if score > 0.4
                 "LOW" otherwise
}
```

### Layer 2 — Scheme Gap (`analytics/scheme_gap_analysis.py`)

```python
# Inputs: scheme_activity JOIN pulse_events (issue=scheme topic)
# 4-way classification:
#   execution_gap  → completion 100% + high beneficiaries + negative sentiment
#   reach_gap      → completion 100% + low beneficiaries + negative sentiment
#   awareness_gap  → completion 100% + high beneficiaries + neutral sentiment
#   performing_well→ completion 100% + positive sentiment
#
# Output → SchemeGap node + HAS_SCHEME_GAP edge + FOR_SCHEME edge + TAGGED_ISSUE edge
```

### Layer 3 — Alias Expander (`nlp/alias_expander.py`)

```python
# During geo_resolve: if location_mention not in aliases.json
# → auto-propose new alias entry to gorakhpur_aliases.json
# → flag for human review (confidence < 0.7)
```

### Layer 4 — Contradiction Detection (`analytics/contradiction_detector.py`)

```python
# Per booth per entity (party/candidate):
# polarity_youtube = avg(polarity) from yt_comment events
# polarity_news    = avg(polarity) from news events
# delta = abs(polarity_youtube - polarity_news)
#
# if delta > 0.5: flag_label = "SWING_INDICATOR"
# if delta > 0.7: flag_label = "STRONG_CONTRADICTION"
#
# Output → ContradictionFlag node + HAS_CONTRADICTION + ABOUT_ENTITY edges
```

### Layer 5 — Narrative Detection (`analytics/narrative_detector.py`)

```python
# Narrative types and their trigger rules:
NARRATIVE_RULES = {
    "anti_incumbency":      lambda events: ruling_party_negative(events, threshold=3),
    "development_positive": lambda events: positive_on_infra_issues(events),
    "corruption_narrative": lambda events: issue_count(events, "corruption") > 2,
    "price_rise_narrative": lambda events: issue_count(events, "inflation") > 2,
    "employment_crisis":    lambda events: issue_count(events, "jobs") > 3,
    "women_safety":         lambda events: issue_count(events, "crime") > 2,
    "scheme_success":       lambda events: positive_on_scheme_mention(events),
    "swing_possible":       lambda flags: contradiction_count(flags) >= 2,
}
# strength = weighted issue/party signal share across booth events
# Output → Narrative node + HAS_NARRATIVE + ABOUT_ISSUE + INVOLVES_PARTY edges
```

---

## 11. UI Data Connections

How each dashboard page connects to the Neo4j graph via FastAPI:

### Page 1 — Constituency Overview (`/ac/{ac_id}/booths`)

```cypher
MATCH (ac:AssemblyConstituency {ac_id: $ac_id})
MATCH (ac)-[:HAS_BOOTH]->(b:Booth)
OPTIONAL MATCH (b)-[:HAS_NARRATIVE]->(n:Narrative)
OPTIONAL MATCH (b)-[:HAS_QUALITY]->(dq:DataQuality)
RETURN ac, collect(b), collect(n), collect(dq)
```

**Widget data connections:**
| Widget | Neo4j Query | Postgres Fallback |
|---|---|---|
| Historical Lean | `(Booth)-[:HAD_RESULT]->(Election)` | `booth_results` |
| Digital Lean | `booth_metrics.digital_lean` | `booth_metrics` |
| Top Issues | `(PulseEvent)-[:TAGGED_ISSUE]->(Issue)` count | `pulse_events` |
| Current MLA | `(Candidate)-[:CONTESTED_IN]->(AC)` where designation='CM' | `candidate_master` |
| Risk Indicators | `(Booth)-[:HAS_NARRATIVE]->(n WHERE n.narrative_type='anti_incumbency')` | `booth_narratives` |

---

### Page 2 — Booth Intelligence (`/booth/{id}/summary`)

```cypher
MATCH (b:Booth {booth_id: $booth_id})
OPTIONAL MATCH (b)-[:HAS_QUALITY]->(dq:DataQuality)
OPTIONAL MATCH (b)-[:HAS_NARRATIVE]->(n:Narrative)
OPTIONAL MATCH (b)-[:HAS_SCHEME_GAP]->(sg:SchemeGap)-[:FOR_SCHEME]->(sc:Scheme)
OPTIONAL MATCH (b)-[:HAS_CONTRADICTION]->(cf:ContradictionFlag)
OPTIONAL MATCH (pe:PulseEvent)-[:AT_BOOTH]->(b)
RETURN b, dq, collect(n), collect(sg), collect(cf),
       collect(pe) ORDER BY pe.published_at DESC LIMIT 20
```

**Widget data connections:**
| Widget | Source | Key Property |
|---|---|---|
| Demographics | `Booth` node | `total_voters`, `male_voters`, `female_voters`, `age_*` |
| Historical Trend | `HAD_RESULT` edge | `bjp_votes`, `sp_votes`, `turnout_pct` per year |
| Pulse Score | `booth_metrics` (Postgres) | `bjp_pulse`, `opp_pulse`, `digital_lean` |
| Top Issues | `PulseEvent → Issue` aggregation | `issue_code`, count, avg polarity |
| Emotion Breakdown | `PulseEvent.emotion` aggregation | anger/frustration/hope % |
| Narrative Shift | `Narrative` node | `narrative_type`, `strength` |
| Scheme Gaps | `SchemeGap` node | `gap_type`, `scheme_id`, `priority` |
| Data Quality | `DataQuality` node | `quality_label`, `quality_reasons[]` |

---

### Page 3 — Candidate Intelligence (`/ac/{ac_id}/candidates`)

```cypher
MATCH (c:Candidate)-[:CONTESTED_IN]->(ac:AssemblyConstituency {ac_id: $ac_id})
MATCH (c)-[:REPRESENTS]->(p:Party)
OPTIONAL MATCH (pe:PulseEvent)-[:MENTIONS_PARTY]->(p)
OPTIONAL MATCH (pe)-[:AT_BOOTH]->(b:Booth)-[:HAS_BOOTH]-(ac)
RETURN c, p, avg(pe.polarity) as party_sentiment,
       count(pe) as mention_count
```

---

### Page 4 — Scheme Intelligence (`/booth/{id}/schemes`)

```cypher
MATCH (b:Booth {booth_id: $booth_id})-[:HAS_SCHEME_GAP]->(sg:SchemeGap)
MATCH (sg)-[:FOR_SCHEME]->(sc:Scheme)
OPTIONAL MATCH (sg)-[:TAGGED_ISSUE]->(i:Issue)
RETURN sc.name, sg.gap_type, sg.priority, sg.beneficiary_count,
       sg.expenditure_inr, collect(i.code) as related_issues
ORDER BY sg.priority DESC
```

---

### Page 7 — Knowledge Graph Explorer

```cypher
// Starting from a booth — expand the full intelligence graph
MATCH (b:Booth {booth_id: $booth_id})
CALL apoc.path.spanningTree(b, {
  relationshipFilter: "HAS_NARRATIVE>|HAS_SCHEME_GAP>|HAS_QUALITY>|
                       HAS_CONTRADICTION>|ABOUT_ISSUE>|FOR_SCHEME>|
                       INVOLVES_PARTY>|TAGGED_ISSUE>",
  maxLevel: 3
}) YIELD path
RETURN path
```

---

## 12. Execution Order

Run in this exact order (dependencies must exist before loading):

```bash
# Step 0: Install dependencies
pip install xlrd==1.2.0 openpyxl pandas neo4j psycopg2 python-dotenv

# Step 1: Database setup
psql $POSTGRES_URL -f db/migrations/001_initial.sql
psql $POSTGRES_URL -f db/migrations/002_quality_narratives.sql
cat graph/constraints.cypher    | cypher-shell -u neo4j -p $NEO4J_PASSWORD
cat graph/constraints_v2.cypher | cypher-shell -u neo4j -p $NEO4J_PASSWORD

# Step 2: Transform existing data (no scraping needed)
python -m etl.transform_geography     # → ac_master, booth_master
python -m etl.transform_candidates    # → candidate_master (depends on ac_master)
python -m etl.transform_panchayats    # → panchayat_master (depends on ac_master)
python -m etl.transform_schemes       # → scheme_master, scheme_activity
python -m etl.transform_voters        # → booth_demographics (depends on booth_master)
python -m etl.transform_census        # → village_demographics
python -m etl.transform_news          # → news_articles (pre-NLP)
python -m etl.transform_affidavit_ocr # → updates candidate_master

# Step 3: Load geography to Neo4j FIRST (all FKs depend on this)
python -m graph.loaders.load_structure    # State → District → AC → Booth
python -m graph.loaders.load_candidates   # Candidate + Party (AC must exist)
python -m graph.loaders.load_panchayats   # Panchayat (AC must exist)

# Step 4: Run scrapers for missing data
python -m ingestion.eci_booth_results  # → booth_results
python -m ingestion.youtube_comments   # → yt_comments
python -m ingestion.news_scraper       # → news_articles (extend)
python -m ingestion.egramswaraj_schemes # → scheme_activity (extend)
python -m ingestion.grievance_scraper  # → grievance_events (NEW)

# Step 5: Run NLP pipeline on all text sources
python -m flows.nlp.flow_sentiment     # news + youtube + grievances → pulse_events

# Step 6: Load pulse events to Neo4j (Booth must exist)
python -m graph.loaders.load_pulse_events   # PulseEvent + AT_BOOTH + TAGGED_ISSUE

# Step 7: Run all 5 intelligence layers
python -m flows.aggregation.flow_full_analytics
# Internally runs:
#   analytics.data_quality        → DataQuality nodes
#   analytics.scheme_gap_analysis → SchemeGap nodes  (requires scheme_activity + pulse_events)
#   analytics.contradiction_detector → ContradictionFlag nodes
#   analytics.narrative_detector  → Narrative nodes

# Step 8: Load intelligence nodes to Neo4j
python -m graph.loaders.load_quality_narratives

# Step 9: Start services
uvicorn api.main:app --reload --port 8000
streamlit run frontend/streamlit/app.py
```

---

## 13. Gap Analysis — What Is Missing Right Now

| Gap | Impact | Fix | Priority |
|---|---|---|---|
| `xlrd` not installed | Cannot read `.xls` files → no scheme data | `pip install xlrd==1.2.0` | P0 |
| No Form-20 booth results | `HAD_RESULT` edges empty, no historical trends | Run `ingestion/eci_booth_results.py` | P0 |
| ceoup JSON has station names but no `part_no` numbers | Cannot generate `booth_id` for all 235 booths | Cross-reference electoral roll `Part No` to station names | P0 |
| Block → AC mapping incomplete | 10 of 20 blocks not mapped | Verify and complete `BLOCK_TO_AC_MAP` dictionary | P1 |
| News CSV thin (103 articles) | Weak sentiment signal | Run `ingestion/news_scraper.py` | P1 |
| No YouTube comments | Digital pulse layer empty | Run `ingestion/youtube_comments.py` | P1 |
| No grievance data | Strongest real-world signal missing | Write + run `ingestion/grievance_scraper.py` | P1 |
| NLP not run on news CSV | `pulse_events` empty → all analytics blocked | Run `flows.nlp.flow_sentiment` | P1 |
| No scheme completion data from eGramSwaraj API | `gap_type = "no_data"` everywhere | Run `ingestion/egramswaraj_schemes.py` | P2 |
| PCA census village → booth mapping | Demographic enrichment broken | Build locality lookup in `gorakhpur_aliases.json` | P2 |

---

*Document version: 2026-05-09*
*Scope: Gorakhpur Urban AC 322, Phase 1 pilot*
*Next: Build Phase 2 — Campierganj AC (320)*
