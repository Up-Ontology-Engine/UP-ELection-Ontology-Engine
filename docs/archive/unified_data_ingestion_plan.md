# Gorakhpur Election Intelligence Platform: Ingestion & Decision Architecture

This document outlines the final, elite-tier ingestion and decision architecture for the Gorakhpur Ontology Engine. It transcends data collection and behavioral capture, introducing **Decision Intelligence, Bot Suppression, and Ground-Truth Validation** to ensure actions are based on stable, verified reality.

---

## 1. The Centralized Configuration (`ingestion_config.json`)

The config remains the backbone, tracking Official Data, News, YouTube, and Field Surveys.

```json
{
  "official_sources": [
    { "id": "eci_booths", "type": "html_scraper", "target_table": "booth_master" },
    { "id": "eci_results", "type": "html_scraper", "target_table": "booth_results", "credibility_score": 1.0, "bias_score": 0.0 },
    { "id": "egramswaraj_schemes", "type": "api_scraper", "target_table": "panchayat_activity" }
  ],
  "youtube_sources": [
    { "id": "air_news_gkp", "lean": "neutral", "scope": "local", "source_type": "yt_comment", "credibility_score": 0.9, "bias_score": 0.1, "capture_engagement": true, "geo_filter_required": false },
    { "id": "sham_sharma", "lean": "pro_govt", "scope": "national", "source_type": "yt_comment", "credibility_score": 0.6, "bias_score": 0.8, "capture_engagement": true, "geo_filter_required": true },
    { "id": "dhruv_rathee", "lean": "critical_govt", "scope": "national", "source_type": "yt_comment", "credibility_score": 0.6, "bias_score": -0.8, "capture_engagement": true, "geo_filter_required": true }
  ],
  "news_sources": [
    { "id": "jagran_gorakhpur", "type": "html_scraper", "source_type": "news_article", "credibility_score": 0.8, "bias_score": 0.3 }
  ],
  "field_sources": [
    { "id": "field_notes_gorakhpur", "type": "manual_form", "source_type": "field_note", "credibility_score": 0.9, "bias_score": 0.3 }
  ],
  "geo_aliases": [ "उत्तर प्रदेश", "UP", "गोरखपुर", "योगी", "Gorakhpur", "campierganj", "pipraich" ]
}
```

---

## 2. End-to-End Intelligence Pipeline

### Phase 1 & 2: Ingestion + Virality & Bot Detection
We fetch comments/news alongside `likes`, `replies`, and `velocity`.
- **Bot/Noise Detection:** If a comment has 10k likes but comes from an account created yesterday with 0 followers, or matches known IT cell spam patterns, it receives a high `bot_suspicion_score`.

### Phase 3 & 4: Deep LLM Extraction & Attribution
The text goes to Groq/Instructor to extract `entity`, `polarity`, `emotion_type`, `intensity_score`, and `inferred_segment`.
- **Segment Confidence Threshold:** If `segment_confidence < 0.7`, the user segment is marked as "Unknown" to prevent fragile assumptions (e.g. assuming "no jobs" always means "youth").
- **Issue Responsibility Mapping:** "No water" is automatically attributed to `local_level` (municipal), not just broadly to "BJP". This isolates candidate anger vs. government anger.

### Phase 5: The Elite Reality-Weight Formula
Before saving the `PulseEvent`, we calculate its exact impact weight. 

```text
event_weight = 
  source_type_weight           // (survey:1.0, news:0.8, yt:0.6)
  × credibility_score          
  × (1 - |bias_score|)         
  × geo_confidence             
  × entity_confidence          
  × intensity_score            // (anger/frustration multiplier)
  × log(1 + engagement_likes)  // (virality multiplier)
  × (1 - bot_suspicion_score)  // (NOISE/BOT SUPPRESSION)
  × e^(-days_old / decay)      
```

### Phase 6: Decision Abstraction & Cross-Booth Context
We do not just look at Booth 223 in isolation. We run analytics to abstract signals into **Decisions**.
- **Temporal Trend Stability:** We compute a `trend_stability_score`. A 2-day spike in water complaints is flagged as noise; a 14-day sustained increase is an actual trend.
- **Cross-Booth Context:** We compute `relative_issue_score = booth_issue_score / district_avg_issue_score`. This determines if an issue is *localized* (Booth 223 only) or *systemic* (entire Gorakhpur).
- **Decision Outputs:** The dashboard abstracts the data into a `risk_score` (high negative intensity on highly responsible issues) and an `opportunity_score` (high positive reception of a specific scheme).

---

## 3. Ground-Truth Anchor Loop (Validation Framework for Booth 223)

To prevent model drift and hallucination buildup, we **STOP feature engineering here** and implement a strict validation loop for Booth 223.

### The Validation Layer
We maintain a `validation_layer` table comparing the system's output against actual ground truth (surveys/past elections).

```sql
CREATE TABLE validation_layer (
  booth_id VARCHAR(30),
  metric_name VARCHAR(50),       -- e.g., "bjp_pulse_score", "top_issue"
  system_output FLOAT,           -- What the engine computed
  ground_truth_expected FLOAT,   -- What field agents/past results show
  error_margin FLOAT,            -- Delta
  validated_at TIMESTAMPTZ
);
```

### Booth 223 Calibration Steps
1. **Run Pipeline on Booth 223:** Ingest all YouTube, News, and Scheme data mapped to Booth 223.
2. **Review Extracted Entities:** Check the `entity_resolution_log`. Did it incorrectly map "Gorakhnath Temple" to a political party? Fix the alias index.
3. **Review Emotion Classification:** Check if "थोड़ी समस्या है" (minor issue) was incorrectly given an `intensity_score` of 0.9. Adjust the LLM prompt.
4. **Compare Ground Truth:** Does the system say Booth 223's top issue is "Jobs", but the ground truth survey says it's "Water"? Adjust the `bot_suspicion_score` and `source_type_weight`.

---

## 4. Seeding Decision Intelligence to Neo4j

We push these abstracted layers directly to the Graph so analysts don't have to write complex SQL.

```cypher
// 1. Create the Pulse Event with Bot suppression and Intensity
CREATE (pe:PulseEvent {
    source_type: "yt_comment",
    issue: "water",
    emotion: "anger",
    intensity: 0.95,
    event_weight: 4.2,
    bot_suspicion: 0.05
})

// 2. Link to Issue with Responsibility Level
MERGE (i:Issue {name: "water", responsible_level: "local_municipal"})
MERGE (pe)-[:ABOUT_ISSUE]->(i)

// 3. Update Booth Decision Scores (Aggregated Periodically)
MATCH (b:Booth {booth_id: "GKP_223"})
SET b.risk_score = 0.85,
    b.opportunity_score = 0.2,
    b.trend_stability_score = 0.92  // 14-day sustained issue
    
// 4. Link Causal Political Event
MERGE (evt:PoliticalEvent {name: "Water Supply Cutoff"})
MERGE (pe)-[:TRIGGERED_BY]->(evt)
```

---

## 5. Final Verdict & Next Steps

This architecture represents the pinnacle of an Election Intelligence Platform. We know the **what, who, how, why, how sure we are, and what action to take.**

**Immediate Next Step:**
Do not add any more features. Begin executing the pipeline exclusively on **Booth 223**, manually validate the JSON extraction outputs, check the error margins in the validation layer, and calibrate the weights.






Complete ETL Pipeline Architecture — UP Election Ontology Engine
What you have in data/data/
File	Type	Contains
eci_electoral_roll_gorakhpur.json	JSON	9 AC numbers/names, ECI constituency metadata
ceoup_gorakhpur_electoral_data.json	JSON	235 polling stations for Gorakhpur Urban, Form-20 info
affidavit_gorakhpur_all_candidates.json	JSON	37 candidates (Urban 2022), 38 (Rural 2022), 53 (LS 2024) — name, party, status
neva_gorakhpur_mla_data.json	JSON	Current MLA name, party, email, phone per constituency
egramswaraj_gorakhpur_panchayat_data.json	JSON	1,273 gram panchayats, 20 blocks, pradhan names, 15,843 elected reps
BlockWiseSummaryReport_2022-2023.xls	XLS	MGNREGA block-wise scheme expenditure 2022-23
BlockWiseSummaryReport_2024-2025.xls	XLS	MGNREGA block-wise scheme expenditure 2024-25
DistrictWiseExpenditureReport.xls	XLS	District-level scheme spending totals
PCA_CDB_0957_F_Census.xls	XLS	Village-level census demographics (Gorakhpur block 0957)
electoral_roll.xlsx + electoral_roll (1).xlsx	XLSX	Seq No, Name, Father/Husband, House No, Age, Gender, Status, EPIC No, Part No
results-20260508043736 (3).csv	CSV	News articles: URL, MobileURL, Date, Title (Hindi + English)
Affidavit PDFs + .txt extractions	PDF/TXT	Raw affidavit OCR text (criminal records, assets)
ETL Pipeline — Full Architecture

┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 0: RAW FILES (data/data/)                                            │
│                                                                             │
│  JSON ──────────────────────────────────────────────────┐                  │
│  eci_electoral_roll_gorakhpur.json                       │                  │
│  ceoup_gorakhpur_electoral_data.json                     │                  │
│  affidavit_gorakhpur_all_candidates.json                 │ EXTRACT          │
│  neva_gorakhpur_mla_data.json                            │                  │
│  egramswaraj_gorakhpur_panchayat_data.json               │                  │
│                                                          │                  │
│  XLS/XLSX ──────────────────────────────────────────────┤                  │
│  BlockWiseSummaryReport_2022-2023.xls                    │                  │
│  BlockWiseSummaryReport_2024-2025.xls                    │                  │
│  DistrictWiseExpenditureReport.xls                       │                  │
│  PCA_CDB_0957_F_Census.xls                               │                  │
│  electoral_roll.xlsx / electoral_roll (1).xlsx           │                  │
│                                                          │                  │
│  CSV ───────────────────────────────────────────────────┘                  │
│  results-20260508043736 (3).csv  (news articles)                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: TRANSFORM — Add connector keys for Neo4j                          │
│                                                                             │
│  etl/transform_geography.py     → adds: state_id, district_id, ac_id       │
│  etl/transform_candidates.py    → adds: candidate_id, party_id, election_id │
│  etl/transform_panchayats.py    → adds: panchayat_id, block_id             │
│  etl/transform_schemes.py       → adds: scheme_id, block_id, gap_type      │
│  etl/transform_voters.py        → adds: booth_id from Part No., agg counts │
│  etl/transform_news.py          → adds: event_id, language detect, NLP     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: LOAD — PostgreSQL Staging (gorakhpur_db)                          │
│                                                                             │
│  ac_master ← geography transform                                            │
│  booth_master ← ceoup polling stations                                      │
│  candidate_master ← affidavit JSON + neva JSON                              │
│  booth_results ← Form-20 / ECI results                                      │
│  scheme_activity ← BlockWise + District XLS                                 │
│  news_articles ← CSV (raw, pre-NLP)                                         │
│  pulse_events ← news_articles AFTER NLP pipeline                            │
│  panchayat_master ← egramswaraj JSON                                        │
│  booth_demographics ← electoral_roll + PCA census (aggregated, no PII)     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │  nlp/pipeline.py (lang_detect → bhashini
                                   │  → groq → geo_resolve → alias_expander)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: NEO4J GRAPH LOAD (graph/loaders/)                                 │
│                                                                             │
│  load_structure.py     → State, District, AC, Booth nodes + hierarchy edges │
│  load_candidates.py    → Candidate, Party nodes + CONTESTED_IN, REPRESENTS  │
│  load_panchayats.py    → Panchayat nodes + LOCATED_IN_AC                    │
│  load_pulse_events.py  → PulseEvent nodes + AT_BOOTH, MENTIONS_PARTY        │
│  load_quality_narratives.py → DataQuality, Narrative, SchemeGap,            │
│                               ContradictionFlag + all intelligence edges    │
└─────────────────────────────────────────────────────────────────────────────┘
Stage 1 — Required Connector Columns per Source
A. Geography (Foundation — everything hangs off this)
Source: eci_electoral_roll_gorakhpur.json + ceoup_gorakhpur_electoral_data.json


EXTRACT              TRANSFORM (add)              NEO4J NODE
─────────────────────────────────────────────────────────────
ac_number (int)  →  ac_id = f"GKP_{ac_number}"  → AssemblyConstituency.ac_id  ← PRIMARY KEY
ac_name (str)    →  ac_name                      → AssemblyConstituency.name
                 →  district_id = "GKP"          → District.district_id
                 →  state_id = "UP"              → State.state_id
part_no (int)    →  booth_id = f"GKP_{ac_number}_{part_no:03d}"  → Booth.booth_id  ← PRIMARY KEY
booth_name (str) →  booth_name                   → Booth.name
Neo4j connection chain:


State{state_id:"UP"} -[:HAS_DISTRICT]-> District{district_id:"GKP"}
  -[:HAS_AC]-> AC{ac_id:"GKP_322"} -[:HAS_BOOTH]-> Booth{booth_id:"GKP_322_045"}
B. Candidates & Parties
Source: affidavit_gorakhpur_all_candidates.json + neva_gorakhpur_mla_data.json


EXTRACT                     TRANSFORM (add)                    NEO4J NODE
───────────────────────────────────────────────────────────────────────────
name (str)              →   candidate_id = slug(name+year)  → Candidate.candidate_id ← PK
party (str)             →   party_id = slug(party)          → Party.party_id         ← PK
status (Accepted/...)   →   status                          → Candidate.status
election (str)          →   election_id = "UP_ASM_2022"     → Election.election_id
constituency (str)      →   ac_id (map from AC name)        → links Candidate → AC
designation (from neva) →   designation                     → Candidate.designation
email (from neva)       →   (not stored in graph, PII-free) → dropped
Neo4j connection chain:


Candidate{candidate_id:"ADITYANATH_2022"} -[:CONTESTED_IN]-> AC{ac_id:"GKP_322"}
Candidate{candidate_id:"ADITYANATH_2022"} -[:REPRESENTS]-> Party{party_id:"BJP"}
Critical connector: ac_id must match exactly what's created in step A.

C. Panchayats
Source: egramswaraj_gorakhpur_panchayat_data.json


EXTRACT                 TRANSFORM (add)                        NEO4J NODE
──────────────────────────────────────────────────────────────────────────
name (str)          →   panchayat_id = slug(block+name)    → Panchayat.panchayat_id ← PK
block (str)         →   block_id = slug(block)             → Panchayat.block
pradhan (str)       →   pradhan_name                       → Panchayat.pradhan_name
elected_members[]   →   total_reps (count)                 → Panchayat.total_reps
male_reps (int)     →   male_reps                          → Panchayat.male_reps
female_reps (int)   →   female_reps                        → Panchayat.female_reps
                    →   ac_id (geo-resolve block → AC)     → links Panchayat → AC
Neo4j connection chain:


Panchayat{panchayat_id:"KHORABAR_ADDA_MOTEERAM"} -[:LOCATED_IN_AC]-> AC{ac_id:"GKP_322"}
AC -[:HAS_PANCHAYAT]-> Panchayat
D. Schemes & Scheme Gaps
Source: BlockWiseSummaryReport_2022-2023.xls, BlockWiseSummaryReport_2024-2025.xls, DistrictWiseExpenditureReport.xls


EXTRACT                     TRANSFORM (add)                     NEO4J NODE
──────────────────────────────────────────────────────────────────────────────
scheme_name (str)       →   scheme_id = slug(scheme_name)    → Scheme.scheme_id ← PK
block_name (str)        →   block_id, ac_id (via block→AC map)
sanctioned_amt (float)  →   sanctioned_amount                → SchemeGap.sanctioned_amount
expenditure (float)     →   expenditure                      → SchemeGap.expenditure
beneficiaries (int)     →   beneficiaries                    → SchemeGap.beneficiaries
completion_pct (float)  →   completion_pct
year (str)              →   fiscal_year                      → SchemeGap.fiscal_year
                        →   gap_type (computed):             → SchemeGap.gap_type
                               execution_gap / reach_gap
                               awareness_gap / performing_well
                        →   booth_id (from geo-resolve)      → links SchemeGap → Booth
Neo4j connection chain:


Booth{booth_id:"GKP_322_045"} -[:HAS_SCHEME_GAP]-> SchemeGap{gap_id:"..."}
SchemeGap -[:FOR_SCHEME]-> Scheme{scheme_id:"MGNREGA"}
SchemeGap -[:TAGGED_ISSUE]-> Issue{code:"jobs"}
E. Voter Demographics (Aggregated, No PII)
Source: electoral_roll.xlsx (cols: Seq No, Name, Father/Husband, House No, Age, Gender, Status, EPIC No, Part No)


EXTRACT         TRANSFORM (aggregate by Part No)       NEO4J NODE / Booth Property
───────────────────────────────────────────────────────────────────────────────────
Part No (int) → booth_id = f"GKP_322_{part_no:03d}" → Booth.booth_id (join key)
Gender (M/F)  → total_voters, male_voters,            → Booth.total_voters
                 female_voters, other_voters            → Booth.male_voters
Age (int)     → age_18_25, age_26_40, age_40_60,      → Booth.age_18_25 (etc.)
                 age_60_plus
Status (str)  → active_voters (Status == 'Active')    → Booth.active_voters
Name          → DROPPED (PII) — only aggregate counts stored
EPIC No       → DROPPED (PII)
Father/Husband→ DROPPED (PII)
No PII enters Neo4j — only booth-level aggregate counts.

F. News Articles → PulseEvents (NLP Required)
Source: results-20260508043736 (3).csv (cols: URL, MobileURL, Date, Title)


EXTRACT         TRANSFORM (NLP pipeline)               NEO4J NODE
──────────────────────────────────────────────────────────────────────────────
URL (str)     → source_url                           → PulseEvent.source_url
Date (dt)     → published_at                         → PulseEvent.published_at
Title (str)   → raw_text                             
              ↓ lang_detect
              → language ("hi"/"en")                 → PulseEvent.language
              ↓ bhashini (if Hindi)
              → translated_text (English)
              ↓ groq llama-3.3-70b extractor
              → polarity (-1.0 to +1.0)              → PulseEvent.polarity
              → confidence (0.0 to 1.0)              → PulseEvent.confidence
              → issue_codes ["water","jobs",...]     → PulseEvent.issue_codes[]
              → party_mentions ["BJP","SP",...]      → PulseEvent.party_mentions[]
              → location_mention (str)
              ↓ geo_resolver
              → booth_id (fuzzy match)               → PulseEvent.booth_id ← JOIN KEY
              → event_id = hash(url+date)            → PulseEvent.event_id  ← PK
              → source_type = "news"                 → PulseEvent.source_type
Neo4j connection chain:


PulseEvent{event_id:"abc123"} -[:AT_BOOTH]-> Booth{booth_id:"GKP_322_045"}
PulseEvent -[:MENTIONS_PARTY]-> Party{party_id:"BJP"}
PulseEvent -[:TAGGED_ISSUE]-> Issue{code:"water"}
Complete Column Requirements for Neo4j Connectivity
This table shows every column each Neo4j node requires and where it comes from:

Neo4j Node	Required Property	Source File	Source Column	Transform
State	state_id	eci_electoral_roll.json	hardcoded	"UP"
State	name	eci_electoral_roll.json	hardcoded	"Uttar Pradesh"
District	district_id	eci_electoral_roll.json	hardcoded	"GKP"
District	name	eci_electoral_roll.json	region	"Gorakhpur"
AssemblyConstituency	ac_id ← PK	eci_electoral_roll.json	number	f"GKP_{number}"
AssemblyConstituency	ac_number	eci_electoral_roll.json	number	int
AssemblyConstituency	name	eci_electoral_roll.json	name	str
Booth	booth_id ← PK	ceoup_gorakhpur.json	part_no	f"GKP_{ac_number}_{part_no:03d}"
Booth	name	ceoup_gorakhpur.json	station_name	str
Booth	ac_id ← FK → AC	ceoup_gorakhpur.json	ac_number	f"GKP_{ac_number}"
Booth	total_voters	electoral_roll.xlsx	Part No (agg)	count by Part No
Booth	male_voters	electoral_roll.xlsx	Gender=='M'	count
Booth	female_voters	electoral_roll.xlsx	Gender=='F'	count
Candidate	candidate_id ← PK	affidavit.json	name + election	slug
Candidate	name	affidavit.json	name	str
Candidate	party_id ← FK → Party	affidavit.json	party	slug
Candidate	ac_id ← FK → AC	affidavit.json	constituency	map name→id
Candidate	election_id	affidavit.json	election	"UP_ASM_2022"
Candidate	status	affidavit.json	status	str
Party	party_id ← PK	affidavit.json	party	slug(BJP→"BJP")
Party	name	affidavit.json	party	str
Panchayat	panchayat_id ← PK	egramswaraj.json	block+name	slug
Panchayat	name	egramswaraj.json	name	str
Panchayat	block	egramswaraj.json	block	str
Panchayat	ac_id ← FK → AC	egramswaraj.json	block	block→AC lookup
Panchayat	pradhan_name	egramswaraj.json	pradhan	str
Panchayat	total_reps	egramswaraj.json	elected_members	len()
Scheme	scheme_id ← PK	BlockWise XLS	scheme_name	slug
Scheme	name	BlockWise XLS	scheme_name	str
PulseEvent	event_id ← PK	news CSV	URL+Date	hash
PulseEvent	source_url	news CSV	URL	str
PulseEvent	published_at	news CSV	Date	datetime
PulseEvent	raw_text	news CSV	Title	str
PulseEvent	polarity	NLP output	groq extract	float
PulseEvent	confidence	NLP output	groq extract	float
PulseEvent	booth_id ← FK → Booth	NLP geo_resolve	location_mention	fuzzy→booth_id
PulseEvent	source_type	hardcoded	—	"news"
SchemeGap	gap_id ← PK	BlockWise XLS	scheme+block	slug
SchemeGap	booth_id ← FK → Booth	BlockWise XLS	block_name	block→booth map
SchemeGap	scheme_id ← FK → Scheme	BlockWise XLS	scheme_name	slug
SchemeGap	gap_type	BlockWise XLS	computed	execution/reach/awareness/well
SchemeGap	beneficiaries	BlockWise XLS	beneficiaries	int
SchemeGap	expenditure	BlockWise XLS	expenditure	float
The 3 Critical Connector Keys (must be consistent everywhere)

booth_id  = f"GKP_{ac_number}_{part_no:03d}"    ← links Booth↔PulseEvent, Booth↔SchemeGap
ac_id     = f"GKP_{ac_number}"                   ← links AC↔Booth, AC↔Candidate, AC↔Panchayat
party_id  = party_name.upper().replace(" ","_")  ← links Candidate↔Party, PulseEvent↔Party
These three keys must be generated identically in every ETL script — if one script writes "GKP_322_045" and another writes "GKP_322_45", Neo4j creates duplicate disconnected nodes.

ETL Script Map

etl/
├── transform_geography.py     ← eci_electoral_roll.json + ceoup.json → ac_master, booth_master
├── transform_candidates.py    ← affidavit.json + neva.json → candidate_master
├── transform_panchayats.py    ← egramswaraj.json → panchayat_master
├── transform_schemes.py       ← BlockWise*.xls + DistrictExpenditure.xls → scheme_activity
├── transform_voters.py        ← electoral_roll.xlsx → booth_demographics (AGGREGATED)
├── transform_census.py        ← PCA_CDB_0957_F_Census.xls → village_demographics
└── transform_news.py          ← results*.csv → news_articles (pre-NLP staging)

graph/loaders/
├── load_structure.py          ← ac_master + booth_master → State/District/AC/Booth nodes
├── load_candidates.py         ← candidate_master → Candidate/Party nodes + edges
├── load_panchayats.py         ← panchayat_master → Panchayat nodes + LOCATED_IN_AC
├── load_schemes.py            ← scheme_activity → Scheme/SchemeGap nodes + edges
├── load_pulse_events.py       ← pulse_events (post-NLP) → PulseEvent nodes + AT_BOOTH
└── load_quality_narratives.py ← analytics outputs → DataQuality/Narrative/ContradictionFlag
What's Currently Missing / Gaps to Fill
Gap	Problem	Fix Needed
booth_id for ceoup stations	ceoup JSON has booth names, no part_no mapping yet	Cross-reference electoral roll Part No to station names
Block → AC mapping	egramswaraj has block names, not AC numbers	Build block_to_ac.json lookup table (20 blocks → 9 ACs)
Form-20 booth results	ECI results redirect, no booth-level vote data yet	Run ingestion/eci_booth_results.py scraper
XLS column headers	xlrd not installed, can't read .xls yet	pip install xlrd==1.2.0 (old format) or convert to xlsx
PulseEvents from news	CSV only has Title + URL — NLP not yet run	Run flows/nlp/flow_sentiment.py on news CSV
Affidavit detail	JSON has only name/party/status, not assets/criminal records	Parse .txt OCR files in data/data/text/
