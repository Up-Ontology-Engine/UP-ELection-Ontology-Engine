# Gorakhpur KG — 5-Day Demo Sprint Plan
> Opinionated, vibe-coding-friendly. Every section has runnable code. Ship a vertical slice, not a skeleton.

---

## Section 1: Gaps & Risks for This 5-Day Sprint

### RISK-01 — Bhashini API Approval Delay (CRITICAL)
Bhashini registration can take 24–48 hours for API key approval. If Day 1 starts and the key isn't ready, the entire NLP pipeline stalls.

**Mitigation:** Register on Day 0 (before sprint starts). Build an `IndicTrans2`-based fallback immediately — it runs locally, no key needed. The pipeline should try Bhashini first, fall back to IndicTrans2 if it fails, and fall back to raw text if both fail. Never block on a single external API.

```
priority: fallback chain
1. Bhashini API (best quality, cloud)
2. IndicTrans2 local (good quality, offline)
3. Pass raw text to LLM with language hint (acceptable quality, always available)
```

### RISK-02 — ECI Website Instability (HIGH)
`ceouttarpradesh.nic.in` goes down during business hours due to government infra. Playwright scraping will randomly fail. Booth PDFs are sometimes corrupt.

**Mitigation:** Pre-download all target pages on Day 0. Save HTML snapshots to disk. Parse from disk, not live. Have P13 (domain) also supply a manually curated `booth_master_gorakhpur_urban.csv` as a fallback seed (100 booths is enough for demo).

### RISK-03 — YouTube Rate Limiting / Blocking (MEDIUM)
yt-dlp aggressive fetching triggers IP bans. `--write-comments` on many videos simultaneously will get blocked.

**Mitigation:** Fetch sequentially, not parallel. Add 3–5 second delays. Pre-select 15–20 videos on Day 0 and start overnight downloads. Have a local cache: if `VIDEO_ID.comments.json` exists, skip re-fetch.

### RISK-04 — Instructor + Groq Schema Failures at Scale (HIGH)
When processing thousands of comments, ~10–20% will fail Pydantic validation even with `max_retries=2`. Unhandled failures break the pipeline.

**Mitigation:** Wrap every extraction in try/except. On schema failure: route to rule-based fallback. On rule failure: write `polarity=0, confidence=0.1` and flag for manual review. Never let one bad comment crash a batch.

### RISK-05 — Geo-Resolution Will Be Sparse (KNOWN, ACCEPTED)
For the 5-day sprint, most pulse events will NOT map to a specific booth — they'll map only to the AC. This is fine for a demo. The dashboard must clearly show:
- Events with `geo_confidence >= 0.8` → shown as booth-level
- Everything else → shown as AC-level aggregate

Do not pretend booth-level precision that doesn't exist. Show `data_confidence` prominently.

### RISK-06 — Too Little Data for Meaningful Pulse Scores (MEDIUM)
If only 500 comments are collected, many booths will show 0 events. The demo will look empty.

**Mitigation:** Also scrape news articles (100+ articles give AC-level signals). Use the eGramSwaraj subset to add governance context nodes — they make the graph look rich even without sentiment. Explicitly label the dashboard: "Showing AC-level pulse (booth-level data: in progress)."

### RISK-07 — Neo4j AuraDB Free Tier Limits
AuraDB free = 5 nodes limit removed but 200MB storage. With 300 booths + voters + pulse events, could exceed.

**Mitigation:** For 5-day demo, run Neo4j Community Edition locally via Docker (`docker run neo4j:5`). One team member hosts it, share via ngrok tunnel. AuraDB paid is $65/month — worth it from Week 2.

### RISK-08 — Scope Creep from "Nice to Have" Features
With 15 people and 5 days, the temptation to add WhatsApp delivery, MGNREGA deep-dive, or voter-level profiling is real. These WILL kill the demo.

**Rule:** If it's not in Section 6 "In Scope", it does not get coded. PM (P1) enforces this ruthlessly.

---

## Section 2: Team Structure — 5 Pods

```
Pod 1 — INFRA + BACKBONE       (3 people)  P2, P3, P15
Pod 2 — DYNAMIC SIGNALS        (3 people)  P4, P5, P13
Pod 3 — NLP + SENTIMENT        (4 people)  P6, P7, P8, P14
Pod 4 — GRAPH + ANALYTICS      (2 people)  P9, P11
Pod 5 — UI + API + PM          (3 people)  P1, P10, P12
```

### Pod Responsibilities (5-day scope only)

| Pod | Owns | Delivers by EOD Day 5 |
|---|---|---|
| Infra+Backbone | DB up, booth_master, candidates, roll_summary | ~300 booths in Postgres + Neo4j, 5–10 candidates with affidavit data |
| Dynamic Signals | YouTube comments, news articles, ETL to pulse_events_raw | 5,000+ raw texts in pulse_events_raw |
| NLP+Sentiment | Full pipeline: detect → translate → extract → geo-resolve | pulse_events table with polarity, issue, confidence, mapped_booth_id |
| Graph+Analytics | Neo4j loaded, aggregation, Cypher query library | booth_metrics in Postgres, AC/booth pulse queryable from Neo4j |
| UI+API+PM | FastAPI + Streamlit dashboard | Live demo: select booth → see pulse + issues + candidates |

### Shared Contract (what each pod produces for the next)

```
Pod 1 → Pod 4:    booth_master CSV, candidate_master CSV
Pod 1 → Pod 3:    alias_index JSON (booth names, wards, localities)
Pod 2 → Pod 3:    pulse_events_raw table (text_raw, source_type, source_id)
Pod 3 → Pod 4:    pulse_events table (filled: polarity, issue, confidence, mapped_booth_id)
Pod 4 → Pod 5:    Cypher queries, booth_metrics table, FastAPI contracts
Pod 5 → all:      .env.example, docker-compose.yml (Day 1)
```

---

## Section 3: 5-Day Execution Plan

### DAY 0 (Before Sprint — evening before Day 1)
**Everyone:**
- Clone the repo, run `docker-compose up`, verify DB connections
- P13: Start manually curating `data/seeds/booth_master_gorakhpur_urban.csv` (booth_id, name, address, locality — 50 rows minimum)
- P4: Start 15–20 YouTube video overnight downloads with yt-dlp
- P15: Submit Bhashini registration form at `bhashini.gov.in`
- P2: Have `docker-compose.yml` ready (Postgres + Neo4j + Redis)

---

### DAY 1 — Foundation

#### Pod 1 — Infra + Backbone
| Time | Task | Owner | Output |
|---|---|---|---|
| 9am | Spin up `docker-compose up`, verify all DBs, run DDL SQL, run Neo4j constraints | P2 | All services green |
| 10am | Start Playwright scraper for ECI booths (Gorakhpur Urban AC) | P3 | booth_master partial |
| 10am | Write PII policy doc, define hashing strategy, create `pii_vault` schema | P15 | Legal go/no-go |
| 12pm | If ECI scraper is blocked → import P13's seed CSV into booth_master | P3 | booth_master populated |
| 2pm | Scrape MyNeta for Gorakhpur Urban candidates (5–10 candidates) | P3 | candidate_master |
| 4pm | Load `electoral_roll_summary` from seed CSV (voter counts per booth — manual if needed) | P3 | roll_summary |
| EOD | Verify: `SELECT count(*) FROM booth_master` returns > 50 rows | P2 | ✓ |

#### Pod 2 — Dynamic Signals
| Time | Task | Owner | Output |
|---|---|---|---|
| 9am | Review overnight yt-dlp downloads, check comment JSON files | P4 | Comment files ready |
| 10am | Write `ingest/youtube_loader.py` to parse yt-dlp JSON → `yt_comments` table | P4 | 1000+ rows |
| 10am | Build `data/seeds/gorakhpur_aliases.json` — locality names, wards, chowks, schools | P13 | Alias seed v1 |
| 12pm | Write `ingest/news_jagran.py` and `ingest/news_amarujala.py` scrapers | P5 | 50+ articles |
| 2pm | Load comments + articles → `pulse_events_raw` (text_raw, source_type, source_id) | P5 | Staging table populated |
| 4pm | Label 100 comments manually (entity, issue, polarity) → `data/labeled/eval_100.jsonl` | P13 | Eval dataset |
| EOD | Verify: `pulse_events_raw` has > 1000 rows | P4 | ✓ |

#### Pod 3 — NLP + Sentiment
| Time | Task | Owner | Output |
|---|---|---|---|
| 9am | Set up Groq API + `instructor` library, test Pydantic schema on 5 examples | P7 | Schema validated |
| 9am | Set up language detection: `langdetect` + `fastText` model | P6 | LangDetect working |
| 10am | Integrate Bhashini API (or IndicTrans2 fallback if key not ready) | P6 | Translation working |
| 12pm | Write full `nlp/pipeline.py` — all stages wired together for 1 text | P7 | End-to-end test |
| 2pm | Run pipeline on 200 comments, review outputs with P13 | P7, P13 | Quality check |
| 2pm | Build alias index from P13's `gorakhpur_aliases.json` | P8 | GeoResolver class |
| 4pm | Fix top 3 systematic errors found in quality check, update lexicon | P7, P13 | Better outputs |
| EOD | `nlp/pipeline.py` processes 1 text end-to-end reliably | P7 | ✓ |

#### Pod 4 — Graph + Analytics
| Time | Task | Owner | Output |
|---|---|---|---|
| 9am | Run Neo4j constraints + indexes (schema locked with P1) | P9 | Neo4j schema live |
| 10am | Write `graph/loaders/load_structure.py` — State/District/AC nodes | P9 | Hierarchy loaded |
| 12pm | Write `graph/loaders/load_booths.py` — Booth nodes from booth_master | P9 | Booths in Neo4j |
| 2pm | Write skeleton `graph/queries/cypher_lib.py` with stub functions | P9 | Stubs ready |
| 2pm | Write `analytics/booth_metrics.sql` aggregation query (stub, no data yet) | P11 | SQL ready |
| 4pm | Load candidates + parties into Neo4j (from P3's data) | P9 | Candidates in graph |
| EOD | `MATCH (b:Booth) RETURN count(b)` returns > 50 | P9 | ✓ |

#### Pod 5 — UI + API + PM
| Time | Task | Owner | Output |
|---|---|---|---|
| 9am | `docker-compose.yml` + `.env.example` committed to repo, shared with all | P1 | Everyone can run locally |
| 9am | FastAPI `main.py` with `/health` endpoint and shared DB clients | P10 | API server running |
| 10am | Streamlit `app.py` skeleton: sidebar AC→Booth selector, 3 page tabs | P12 | App loads |
| 11am | Define API contract doc (5 endpoints, request/response shape) | P1 | `docs/api-contract.md` |
| 12pm | FastAPI `GET /ac/{ac_id}/booths` — returns booth list from Postgres | P10 | Endpoint working |
| 2pm | Streamlit: connect sidebar to `/ac/{ac_id}/booths`, populate dropdown | P12 | Dropdown has real booths |
| 4pm | FastAPI `GET /booth/{booth_id}/summary` — returns booth metadata + roll summary | P10 | Endpoint working |
| EOD | Streamlit shows real booth names when Gorakhpur Urban is selected | P12 | ✓ |

**Day 1 Integration Check (5pm):** P1 runs: select AC → see booth dropdown → click booth → see voter counts. If this works, Day 1 is a success.

---

### DAY 2 — NLP Pipeline Running on Real Data

#### Pod 1
| Task | Owner |
|---|---|
| Scrape eGramSwaraj for 5–10 Gorakhpur Urban panchayats (manual if API fails) | P3 |
| Load panchayat data → `panchayat_master` + `panchayat_activity` | P3 |
| Fuzzy-match panchayat names to booth localities → `booth_panchayat_mapping` | P2 |
| Verify all tables have data, fix any ETL bugs from Day 1 | P2, P3 |

#### Pod 2
| Task | Owner |
|---|---|
| Collect more YouTube comments (target: 5000+ total) from 10+ more videos | P4 |
| Scrape 100+ more news articles, deduplicate by URL hash | P5 |
| Expand `gorakhpur_aliases.json` with ward names from manual research | P13 |
| Load all new data into `pulse_events_raw` | P5 |

#### Pod 3
| Task | Owner |
|---|---|
| Run NLP pipeline on ALL rows in `pulse_events_raw` in batches of 50 | P7 |
| Store results in `pulse_events` table (polarity, issue, confidence, llm_output) | P7 |
| Run geo-resolution on all `location_mention` fields from P7's output | P8 |
| Write `mapped_booth_id` + `geo_confidence` back to `pulse_events` | P8 |
| Quality audit: run 50 labeled samples through pipeline, measure accuracy | P6, P14 |
| Fix top errors, update political lexicon | P13 |

#### Pod 4
| Task | Owner |
|---|---|
| Load `PulseEvent` nodes into Neo4j from `pulse_events` (first batch) | P9 |
| Wire `PulseEvent –[:MENTIONS_LOCATION]→ Booth` where geo_confidence >= 0.8 | P9 |
| Wire `PulseEvent –[:ABOUT_ISSUE]→ Issue` for all events | P9 |
| Run booth_metrics aggregation query on Postgres — inspect results | P11 |
| Write `booth_metrics` first rows — even if sparse | P11 |

#### Pod 5
| Task | Owner |
|---|---|
| FastAPI `GET /booth/{booth_id}/pulse` — returns BJP/opp scores from booth_metrics | P10 |
| FastAPI `GET /booth/{booth_id}/issues` — returns top 3 issues with scores | P10 |
| Streamlit: Booth Profile page — pulse bar chart (BJP vs opp) using Plotly | P12 |
| Streamlit: Issues section — horizontal bar chart, top 3 | P12 |
| PM sync: review what's working, adjust Day 3 priorities | P1 |

**Day 2 Integration Check (5pm):** P1 runs: select booth → see pulse chart + top issues (even if data is thin). Candidates panel not required yet.

---

### DAY 3 — Full Vertical Slice Working

#### Pod 1
| Task | Owner |
|---|---|
| Polish booth_master: add lat/lon from manual geocoding of 20 key booths | P3 |
| Link panchayat activities to Neo4j: `Panchayat –[:HAS_ACTIVITY]→ Activity` | P2 |
| Final data quality pass: fill gaps in roll_summary, candidates | P3 |

#### Pod 2
| Task | Owner |
|---|---|
| Second quality pass on news articles — ensure Gorakhpur-specific content only | P5 |
| Add 500+ more comments targeting specific issues (search "gorakhpur pani", "bijli gorakhpur") | P4 |
| Label 50 more edge cases for NLP eval (Bhojpuri-heavy, mixed language) | P13, P14 |

#### Pod 3
| Task | Owner |
|---|---|
| Re-run pipeline on all pulse_events_raw (incremental — only new rows) | P7 |
| Improve geo-resolution: add more aliases from P13, rerun on all low-confidence events | P8 |
| Integrate rule-based fallback: run lexicon classifier on confidence < 0.6 events | P6 |
| Write `final_polarity` column: LLM if confidence >= 0.6, rule-based otherwise | P6 |
| Run full eval: accuracy on 150 labeled samples | P14 |

#### Pod 4
| Task | Owner |
|---|---|
| Implement all 5 key Cypher queries from Section 5 | P9 |
| Wire Cypher queries to FastAPI (P9 provides functions, P10 calls them) | P9 |
| Compute 7-day rolling booth_metrics — write to Postgres | P11 |
| Write `GET /booth/{id}/comments` — top 5 backing comments per booth | P11 |
| Add panchayat governance context: link 5–10 panchayats to booths in graph | P9 |

#### Pod 5
| Task | Owner |
|---|---|
| Streamlit: Candidate Panel tab — name, party, criminal cases, assets, education | P12 |
| Streamlit: Comments feed — 5 backing comments with polarity color coding | P12 |
| Streamlit: Add data_confidence indicator ("Based on N events, confidence: Medium") | P12 |
| FastAPI: All 5 endpoints complete, tested with real data | P10 |
| PM: Validate full flow end-to-end, file bugs for Day 4 | P1 |

**Day 3 Gate:** Full vertical slice works. Select AC → Booth → see pulse + issues + candidates + comments. Even if data is thin.

---

### DAY 4 — Polish, Robustness, Demo Prep

#### All Pods
| Task | Owner |
|---|---|
| Bug fix: any broken pipeline steps from Day 3 demo | P7, P9 |
| Add error states to dashboard: "No data yet" gracefully | P12 |
| Re-run full NLP pipeline on all accumulated data | P7 |
| Improve booth_metrics: add issue_breakdown JSONB | P11 |
| Add AC-level overview: map/table of all booths colored by pulse | P12 |
| FastAPI caching: add `@functools.lru_cache` for Cypher queries | P10 |
| Load small governance subset (5 panchayats) into Neo4j for demo richness | P9 |
| Deploy Streamlit to Streamlit Cloud, FastAPI to Railway | P2 |
| Write demo walkthrough script (`docs/demo-script.md`) | P1 |
| Manual data validation: P13 checks 20 booth pulse scores against intuition | P13 |

---

### DAY 5 — Demo Day

| Time | Task | Owner |
|---|---|---|
| 9am | Final data reload: re-run all pipelines with latest data | P7, P9 |
| 10am | Full demo rehearsal — P1 walks through script, others identify gaps | All |
| 11am | Fix critical bugs found in rehearsal (2h budget) | P7, P10, P12 |
| 1pm | Final deploy: Streamlit Cloud + Railway updated | P2 |
| 2pm | Demo for stakeholders | P1 |
| 4pm | Retrospective: what's working, what breaks under pressure | All |
| EOD | Draft Week 2 plan based on demo feedback | P1 |

---

## Section 4: Deterministic Multilingual Sentiment Architecture

### 4.1 Complete Pydantic Schema

```python
# nlp/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from enum import Enum

class EntityType(str, Enum):
    PARTY     = "party"
    CANDIDATE = "candidate"
    SCHEME    = "scheme"
    ISSUE     = "issue"
    GOVT      = "govt"

class IssueType(str, Enum):
    WATER        = "water"
    ROADS        = "roads"
    ELECTRICITY  = "electricity"
    JOBS         = "jobs"
    WOMEN_SAFETY = "women_safety"
    PRICE_RISE   = "price_rise"
    FARMER       = "farmer"
    SUGARCANE    = "sugarcane"
    HEALTH       = "health"
    EDUCATION    = "education"
    CORRUPTION   = "corruption"
    LAW_ORDER    = "law_order"
    OTHER        = "other"

class SentimentStatement(BaseModel):
    entity: str = Field(
        ...,
        description="Entity name as it appears or is clearly implied. E.g. 'BJP', 'Yogi', 'SP', 'Akhilesh'"
    )
    entity_type: EntityType
    issue: Optional[IssueType] = Field(
        None,
        description="The issue this sentiment is about. Null if sentiment is general."
    )
    polarity: Literal[-1, 0, 1] = Field(
        ...,
        description="-1=negative/criticism, 0=neutral/factual, 1=positive/praise"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Your certainty that this extraction is correct."
    )
    location_mention: Optional[str] = Field(
        None,
        description="Raw location text if any geographic reference exists. E.g. 'Deoria Naka', 'Ward 12', 'Ramgarh school'"
    )
    language: str = Field(
        ...,
        description="Language of original text: hi=Hindi, bho=Bhojpuri, en=English, mix=mixed"
    )
    evidence: str = Field(
        ...,
        description="1–4 word phrase from the text that most directly justifies your polarity. Quote from original."
    )

    @field_validator("entity")
    @classmethod
    def normalize_entity(cls, v: str) -> str:
        # Normalize common aliases at schema level
        mappings = {
            "भाजपा": "BJP", "bjp": "BJP", "कमल": "BJP",
            "समाजवादी": "SP", "सपा": "SP", "साइकिल": "SP",
            "बसपा": "BSP", "हाथी": "BSP",
            "योगी": "Yogi Adityanath", "yogi": "Yogi Adityanath",
            "अखिलेश": "Akhilesh Yadav", "akhilesh": "Akhilesh Yadav",
        }
        return mappings.get(v.lower().strip(), v.strip())

class ExtractionResult(BaseModel):
    statements: List[SentimentStatement] = Field(
        default_factory=list,
        description="One record per entity/issue/polarity combination found."
    )
    primary_language: str = Field(
        ...,
        description="Dominant language of the input text."
    )
    contains_bhojpuri: bool = Field(
        False,
        description="True if Bhojpuri words or dialect detected."
    )
    is_political: bool = Field(
        True,
        description="False if text is completely irrelevant to politics/governance."
    )

class PipelineResult(BaseModel):
    """Full output of the NLP pipeline for one text unit."""
    source_id: str
    source_type: str
    text_raw: str
    text_normalized_hi: Optional[str]
    language_detected: str
    translation_method: Optional[str]   # bhashini | indicTrans2 | none
    extraction: ExtractionResult
    extraction_method: str              # llm | rule_based | llm+rule_fallback
    geo_resolution: Optional[dict]      # {mapped_booth_id, mapped_ac_id, geo_confidence}
    final_polarity: Optional[int]
    final_issue: Optional[str]
    final_confidence: float
    processing_errors: List[str] = Field(default_factory=list)
```

---

### 4.2 Bhashini Integration — Step by Step

```python
# nlp/bhashini.py
import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

BHASHINI_PIPELINE_URL = (
    "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
)

# Language code mapping for Bhashini
LANG_CODE_MAP = {
    "bho": "bho",   # Bhojpuri
    "hi": "hi",     # Hindi
    "en": "en",     # English
    "mix": "hi",    # Mixed → treat as Hindi target
}

def _build_bhashini_payload(text: str, source_lang: str, target_lang: str = "hi") -> dict:
    return {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_lang,
                        "targetLanguage": target_lang,
                    },
                    "serviceId": "",   # Bhashini auto-selects best model
                },
            }
        ],
        "inputData": {
            "input": [{"source": text}],
            "audio": [],
        },
    }

def translate_via_bhashini(
    text: str,
    source_lang: str = "bho",
    target_lang: str = "hi",
) -> tuple[str, str]:
    """
    Returns (translated_text, method_name).
    method_name is 'bhashini' on success, 'failed' on error.
    """
    api_key = os.environ["BHASHINI_API_KEY"]
    user_id = os.environ["BHASHINI_USER_ID"]

    headers = {
        "userID": user_id,
        "ulcaApiKey": api_key,
        "Content-Type": "application/json",
    }
    payload = _build_bhashini_payload(text, source_lang, target_lang)

    try:
        resp = requests.post(
            BHASHINI_PIPELINE_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        translated = (
            resp.json()["pipelineResponse"][0]["output"][0]["target"]
        )
        return translated, "bhashini"
    except Exception as e:
        logger.warning(f"Bhashini failed: {e}")
        return text, "failed"   # return original if translation fails


def translate_via_indictrans2(text: str, source_lang: str = "bho") -> tuple[str, str]:
    """
    Fallback: IndicTrans2 via local model or Hugging Face inference.
    Install: pip install ctranslate2 sentencepiece
    Model: ai4bharat/indictrans2-indic-indic-dist-200M
    """
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        # NOTE: Load these once at module level in production, not per-call
        model_name = "ai4bharat/indictrans2-indic-indic-dist-200M"
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, trust_remote_code=True)

        src_lang = "bho_Deva" if source_lang == "bho" else "hin_Deva"
        tgt_lang = "hin_Deva"

        inputs = tokenizer(text, return_tensors="pt", src_lang=src_lang)
        outputs = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.lang_code_to_id[tgt_lang],
            max_length=512
        )
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated, "indictrans2"
    except Exception as e:
        logger.error(f"IndicTrans2 also failed: {e}")
        return text, "none"


def normalize_text(text: str, detected_lang: str) -> tuple[str, str]:
    """
    Main entry point. Returns (normalized_hindi_text, translation_method).
    If text is already Hindi or English, pass through.
    """
    if detected_lang in ("hi", "en"):
        return text, "none"   # no translation needed

    # Try Bhashini first
    translated, method = translate_via_bhashini(text, source_lang=detected_lang)
    if method == "bhashini":
        return translated, "bhashini"

    # Fallback to IndicTrans2
    translated, method = translate_via_indictrans2(text, source_lang=detected_lang)
    return translated, method
```

---

### 4.3 Language Detection

```python
# nlp/lang_detect.py
import re
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

DetectorFactory.seed = 42   # deterministic

# Bhojpuri-specific word patterns (not in standard Hindi dictionaries)
BHOJPURI_MARKERS = [
    r"\bहऊ\b", r"\bहऊँ\b", r"\bबाड़े\b", r"\bबाड़ी\b",
    r"\bरहल\b", r"\bरहलीं\b", r"\bकहत\b", r"\bजात\b",
    r"\bखाईं\b", r"\bपइसा\b", r"\bनिकलल\b", r"\bमिलल\b",
    r"\bबनल\b", r"\bकइल\b", r"\bआईल\b", r"\bगइल\b",
    r"\bएहिजा\b", r"\bउहाँ\b", r"\bकवनो\b", r"\bहमनी\b",
    r"\bतोहनी\b", r"\bरउआ\b", r"\bईहाँ\b",
]

def detect_language(text: str) -> str:
    """
    Returns: 'hi', 'bho', 'en', 'mix', or 'unknown'
    """
    if not text or len(text.strip()) < 5:
        return "unknown"

    # Check for Bhojpuri markers first (langdetect can't distinguish bho from hi)
    bhojpuri_hits = sum(
        1 for pat in BHOJPURI_MARKERS if re.search(pat, text)
    )
    if bhojpuri_hits >= 2:
        return "bho"
    if bhojpuri_hits == 1:
        return "mix"   # one bhojpuri word in otherwise Hindi text

    try:
        lang = detect(text)
        if lang == "hi":
            return "hi"
        if lang in ("en", "en-GB", "en-US"):
            return "en"
        # For Devanagari text that langdetect classifies as mr/ne/sa → treat as Hindi
        if lang in ("mr", "ne", "sa"):
            return "hi"
        return lang
    except LangDetectException:
        return "unknown"
```

---

### 4.4 LLM Extraction with Instructor

```python
# nlp/extractor.py
import os
import instructor
from groq import Groq
from .schemas import ExtractionResult, SentimentStatement, EntityType, IssueType
import logging

logger = logging.getLogger(__name__)

# Initialize Instructor-patched Groq client once at module level
_groq_client = instructor.from_groq(
    Groq(api_key=os.environ["GROQ_API_KEY"]),
    mode=instructor.Mode.JSON,
)

SYSTEM_PROMPT = """\
You are a political sentiment extractor specializing in Uttar Pradesh elections, India.

STRICT RULES — follow exactly:
1. Output ONLY valid JSON matching the schema. Zero prose, zero markdown, zero explanation.
2. Recognized parties: BJP, SP, BSP, Congress, AAP, RLD. Use exact English spelling.
3. Recognized candidates for Gorakhpur Urban: use exact name. Common ones: Yogi Adityanath (BJP), Subhawati Shukla (BJP), local SP/BSP candidates.
4. Issues — use ONLY these codes: water, roads, electricity, jobs, women_safety, price_rise, farmer, sugarcane, health, education, corruption, law_order, other
5. polarity: 1=positive/praise/support, -1=negative/criticism/complaint, 0=neutral/factual/informational
6. confidence: 0.0–1.0. Use < 0.5 when text is ambiguous or sarcastic.
7. evidence: copy 1–4 words directly from the original text that most justify the polarity.
8. location_mention: any ward, mohalla, village, school, chowk, road name. Include raw text.
9. One SentimentStatement per distinct entity+issue combination.
10. If text is irrelevant to politics/governance, set is_political=false and return empty statements.
11. Sarcasm: in Hindi/Bhojpuri political discourse, heavy praise often = sarcasm → polarity=-1, confidence=0.6.

GORAKHPUR CONTEXT (use to resolve ambiguous references):
- "sarkar" without qualifier usually = BJP government (UP state)
- "netaji", "cycle wale" = SP/Akhilesh Yadav
- "behan ji", "haathi" = BSP/Mayawati
- "yogi" = CM Yogi Adityanath (BJP)
- "double engine" = BJP both state + center
- Local issues: sugarcane mill payments (गन्ना भुगतान), river flooding (flood/बाढ़), CM's home district = high expectations
"""

def extract_from_normalized_text(normalized_text: str) -> ExtractionResult:
    """
    Main LLM extraction. Returns ExtractionResult.
    Instructor handles retries and schema validation.
    """
    try:
        result = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_model=ExtractionResult,
            max_retries=2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract sentiment from this text:\n\n{normalized_text}"},
            ],
            temperature=0.0,   # deterministic
        )
        return result
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        # Return empty result — will trigger rule-based fallback
        return ExtractionResult(
            statements=[],
            primary_language="unknown",
            contains_bhojpuri=False,
            is_political=False,
        )
```

---

### 4.5 Rule-Based Fallback (Political Lexicon)

```python
# nlp/rule_classifier.py
import re
from .schemas import ExtractionResult, SentimentStatement, EntityType, IssueType

# ─── Lexicon ───────────────────────────────────────────────────────────────

PARTY_PATTERNS: dict[str, list[str]] = {
    "BJP": [
        "bjp", "भाजपा", "भारतीय जनता", "कमल", "lotus", "sarkar", "सरकार",
        "yogi", "योगी", "modi", "मोदी", "double engine", "डबल इंजन",
    ],
    "SP": [
        "sp", "समाजवादी", "सपा", "cycle", "साइकिल", "akhilesh", "अखिलेश",
        "netaji", "नेताजी", "mulayam", "मुलायम",
    ],
    "BSP": [
        "bsp", "बसपा", "बहुजन", "elephant", "हाथी", "mayawati", "मायावती", "behan ji",
    ],
    "Congress": [
        "congress", "कांग्रेस", "inc", "rahul", "राहुल", "priyanka", "प्रियंका",
    ],
}

ISSUE_PATTERNS: dict[str, list[str]] = {
    "water":        ["पानी", "water", "नल", "handpump", "हैंडपंप", "पेयजल", "drinking water"],
    "roads":        ["सड़क", "road", "गड्ढे", "pothole", "खराब सड़क", "पक्की सड़क"],
    "electricity":  ["बिजली", "bijli", "light", "load shedding", "लोड शेडिंग", "कटौती"],
    "jobs":         ["बेरोजगारी", "नौकरी", "रोजगार", "job", "unemployment", "rojgar"],
    "price_rise":   ["महंगाई", "inflation", "price hike", "महंगा", "gas", "petrol", "दाम"],
    "farmer":       ["किसान", "kisan", "farmer", "खेती", "फसल", "crop"],
    "sugarcane":    ["गन्ना", "sugarcane", "ganna", "चीनी मिल", "sugar mill", "भुगतान"],
    "women_safety": ["महिला", "woman", "rape", "safety", "बेटी", "सुरक्षा", "darinda"],
    "health":       ["hospital", "अस्पताल", "doctor", "डॉक्टर", "swasthya", "स्वास्थ्य"],
    "education":    ["school", "स्कूल", "college", "शिक्षा", "education", "teacher", "शिक्षक"],
    "corruption":   ["भ्रष्टाचार", "corruption", "घोटाला", "scam", "riswat", "रिश्वत"],
    "law_order":    ["law order", "कानून व्यवस्था", "crime", "अपराध", "police", "police"],
}

POSITIVE_TERMS = [
    "अच्छा", "बढ़िया", "शानदार", "विकास", "तरक्की", "खुश", "धन्यवाद",
    "कमाल", "great", "best", "achha", "badiya", "shukriya", "thank",
    "improve", "development", "prayas", "प्रयास",
]
NEGATIVE_TERMS = [
    "बुरा", "खराब", "बेकार", "झूठ", "धोखा", "नाराज", "परेशान",
    "fraud", "liar", "jhuth", "dhoka", "fail", "नहीं", "कुछ नहीं",
    "भ्रष्ट", "गुंडा", "निराश", "बर्बाद",
]

# ─── Classifier ────────────────────────────────────────────────────────────

def _find_entity(text_lower: str) -> tuple[str | None, str]:
    for party, patterns in PARTY_PATTERNS.items():
        for pat in patterns:
            if pat.lower() in text_lower:
                return party, "party"
    return None, "unknown"

def _find_issue(text_lower: str) -> str | None:
    for issue, patterns in ISSUE_PATTERNS.items():
        for pat in patterns:
            if pat.lower() in text_lower:
                return issue
    return None

def _find_polarity(text_lower: str) -> tuple[int, float]:
    pos = sum(1 for t in POSITIVE_TERMS if t.lower() in text_lower)
    neg = sum(1 for t in NEGATIVE_TERMS if t.lower() in text_lower)
    if neg > pos:
        return -1, min(0.5 + neg * 0.1, 0.85)
    if pos > neg:
        return 1, min(0.5 + pos * 0.1, 0.85)
    return 0, 0.4

def rule_based_extract(text: str) -> ExtractionResult:
    """
    Simple keyword-matching fallback. Low precision, but never crashes.
    Used when LLM confidence < 0.6 or LLM errors.
    """
    text_lower = text.lower()
    entity, entity_type = _find_entity(text_lower)
    issue = _find_issue(text_lower)
    polarity, confidence = _find_polarity(text_lower)

    if entity is None:
        return ExtractionResult(
            statements=[],
            primary_language="hi",
            contains_bhojpuri=False,
            is_political=False,
        )

    stmt = SentimentStatement(
        entity=entity,
        entity_type=EntityType(entity_type),
        issue=IssueType(issue) if issue else None,
        polarity=polarity,
        confidence=confidence,
        location_mention=None,
        language="hi",
        evidence="(rule-based)",
    )
    return ExtractionResult(
        statements=[stmt],
        primary_language="hi",
        contains_bhojpuri=False,
        is_political=True,
    )
```

---

### 4.6 Full Pipeline Orchestrator

```python
# nlp/pipeline.py
import uuid
import logging
from .lang_detect import detect_language
from .bhashini import normalize_text
from .extractor import extract_from_normalized_text
from .rule_classifier import rule_based_extract
from .geo_resolver import GeoResolver
from .schemas import PipelineResult

logger = logging.getLogger(__name__)

# Load geo resolver once at module level
_geo_resolver: GeoResolver | None = None

def get_geo_resolver() -> GeoResolver:
    global _geo_resolver
    if _geo_resolver is None:
        import json, os
        alias_path = os.environ.get("ALIAS_INDEX_PATH", "data/seeds/gorakhpur_aliases.json")
        with open(alias_path) as f:
            alias_data = json.load(f)
        _geo_resolver = GeoResolver(alias_data)
    return _geo_resolver

def process_one(
    text_raw: str,
    source_id: str,
    source_type: str,
    confidence_threshold: float = 0.6,
) -> PipelineResult:
    errors = []

    # ── Stage 1: Language Detection ──────────────────────────────
    lang = detect_language(text_raw)

    # ── Stage 2: Text Cleaning ───────────────────────────────────
    import re
    text_clean = re.sub(r"https?://\S+", "", text_raw)          # remove URLs
    text_clean = re.sub(r"@\w+", "", text_clean)                # remove @mentions
    text_clean = re.sub(r"(.)\1{3,}", r"\1\1", text_clean)      # collapse "aaaa"→"aa"
    text_clean = text_clean.strip()

    # ── Stage 3: Normalization (Bhashini / fallback) ─────────────
    if lang in ("bho", "mix"):
        normalized, translation_method = normalize_text(text_clean, detected_lang=lang)
    else:
        normalized, translation_method = text_clean, "none"

    # ── Stage 4a: LLM Extraction ─────────────────────────────────
    extraction = extract_from_normalized_text(normalized)
    extraction_method = "llm"

    # ── Stage 4b: Rule-Based Fallback ────────────────────────────
    needs_fallback = (
        not extraction.statements
        or all(s.confidence < confidence_threshold for s in extraction.statements)
    )
    if needs_fallback:
        rule_extraction = rule_based_extract(normalized)
        if rule_extraction.statements:
            extraction = rule_extraction
            extraction_method = "rule_based"
        elif extraction.statements:
            extraction_method = "llm+rule_fallback"  # kept LLM low-conf

    # ── Stage 5: Geo Resolution ───────────────────────────────────
    geo_info = None
    for stmt in extraction.statements:
        if stmt.location_mention:
            resolver = get_geo_resolver()
            geo_info = resolver.resolve(stmt.location_mention)
            break   # use first resolved location

    # ── Stage 6: Final Values ─────────────────────────────────────
    final_polarity = None
    final_issue = None
    final_confidence = 0.0

    if extraction.statements:
        best = max(extraction.statements, key=lambda s: s.confidence)
        final_polarity = best.polarity
        final_issue = best.issue.value if best.issue else None
        final_confidence = best.confidence

    return PipelineResult(
        source_id=source_id,
        source_type=source_type,
        text_raw=text_raw,
        text_normalized_hi=normalized if normalized != text_raw else None,
        language_detected=lang,
        translation_method=translation_method,
        extraction=extraction,
        extraction_method=extraction_method,
        geo_resolution=geo_info,
        final_polarity=final_polarity,
        final_issue=final_issue,
        final_confidence=final_confidence,
        processing_errors=errors,
    )

def process_batch(rows: list[dict], batch_size: int = 50) -> list[PipelineResult]:
    """Process a list of {text_raw, source_id, source_type} dicts."""
    results = []
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        for row in batch:
            try:
                result = process_one(
                    text_raw=row["text_raw"],
                    source_id=row["source_id"],
                    source_type=row["source_type"],
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed on source_id={row.get('source_id')}: {e}")
        logger.info(f"Processed {min(i+batch_size, len(rows))}/{len(rows)}")
    return results
```

---

### 4.7 Geo Resolver

```python
# nlp/geo_resolver.py
from thefuzz import process as fuzz_process
from typing import Optional

class GeoResolver:
    """
    Resolves free-text location mentions to booth_id or ac_id.
    alias_data format:
    {
      "Deoria Naka": {"id": "GKP_U_045", "type": "booth", "name": "Booth 45"},
      "Civil Lines": {"id": "GKP_U_012", "type": "booth", "name": "Booth 12"},
      "Gorakhpur Urban": {"id": "GKP_U", "type": "ac", "name": "Gorakhpur Urban"},
      ...
    }
    """
    def __init__(self, alias_data: dict):
        self.aliases = alias_data
        self.alias_keys = list(alias_data.keys())

    def resolve(self, location_text: str, threshold: int = 75) -> Optional[dict]:
        if not location_text or len(location_text) < 3:
            return None

        match, score = fuzz_process.extractOne(
            location_text,
            self.alias_keys,
        )

        if score >= threshold:
            entry = self.aliases[match]
            geo_confidence = round(score / 100.0, 3)
            return {
                "matched_text": match,
                "mapped_id": entry["id"],
                "mapped_type": entry["type"],    # "booth" or "ac"
                "mapped_booth_id": entry["id"] if entry["type"] == "booth" else None,
                "mapped_ac_id": entry["id"] if entry["type"] == "ac" else "GKP_U",
                "geo_confidence": geo_confidence,
            }

        # Low confidence — map to AC level only
        return {
            "matched_text": None,
            "mapped_id": "GKP_U",
            "mapped_type": "ac",
            "mapped_booth_id": None,
            "mapped_ac_id": "GKP_U",
            "geo_confidence": 0.3,
        }
```

---

## Section 5: Cypher Queries & FastAPI Endpoints

### 5.1 Key Cypher Queries

```cypher
// ── QUERY 1: AC-level pulse summary ────────────────────────────────────────
// Used by: dashboard AC overview page
// Returns: BJP and opposition aggregate pulse for Gorakhpur Urban last 7 days

MATCH (a:AssemblyConstituency {ac_id: $ac_id})
      <-[:MENTIONS_LOCATION]-(pe:PulseEvent)
WHERE pe.created_at >= datetime() - duration({days: 7})
  AND pe.entity_type = 'party'
RETURN
  pe.entity                                          AS entity,
  round(avg(pe.polarity * pe.confidence) * 100) / 100 AS pulse_score,
  count(pe)                                          AS event_count,
  collect(DISTINCT pe.issue)[0..5]                  AS top_issues
ORDER BY pulse_score DESC;
```

```cypher
// ── QUERY 2: Booth-level pulse (BJP vs opposition) ──────────────────────────
// Used by: booth profile page — main pulse chart
// Returns: pulse scores per party for this booth, rolling 7 days

MATCH (b:Booth {booth_id: $booth_id})
      <-[:MENTIONS_LOCATION]-(pe:PulseEvent)
WHERE pe.created_at >= datetime() - duration({days: $days})
  AND pe.final_polarity IS NOT NULL
WITH pe.entity AS entity,
     pe.polarity AS polarity,
     pe.confidence AS conf
WHERE entity IN ['BJP', 'SP', 'BSP', 'Congress']
RETURN
  entity,
  round(avg(polarity * conf) * 100) / 100 AS pulse_score,
  count(*) AS event_count
ORDER BY pulse_score DESC;
```

```cypher
// ── QUERY 3: Top issues per booth ───────────────────────────────────────────
// Used by: booth profile — issues radar chart

MATCH (b:Booth {booth_id: $booth_id})
      <-[:MENTIONS_LOCATION]-(pe:PulseEvent)
      -[:ABOUT_ISSUE]->(i:Issue)
WHERE pe.created_at >= datetime() - duration({days: 30})
RETURN
  i.name                                              AS issue,
  count(pe)                                           AS mention_count,
  round(avg(pe.polarity) * 100) / 100                AS avg_polarity,
  sum(CASE WHEN pe.polarity = -1 THEN 1 ELSE 0 END)  AS negative_count,
  sum(CASE WHEN pe.polarity = 1  THEN 1 ELSE 0 END)  AS positive_count
ORDER BY mention_count DESC
LIMIT 5;
```

```cypher
// ── QUERY 4: Recent backing comments for a booth ────────────────────────────
// Used by: booth profile — comments feed

MATCH (b:Booth {booth_id: $booth_id})
      <-[:MENTIONS_LOCATION]-(pe:PulseEvent)
WHERE pe.source_type IN ['youtube', 'news']
  AND pe.final_polarity IS NOT NULL
  AND pe.final_confidence >= 0.6
RETURN
  pe.event_id         AS event_id,
  pe.text_raw         AS text,
  pe.entity           AS entity,
  pe.final_polarity   AS polarity,
  pe.issue            AS issue,
  pe.final_confidence AS confidence,
  pe.source_type      AS source,
  pe.created_at       AS created_at
ORDER BY pe.created_at DESC
LIMIT $limit;
```

```cypher
// ── QUERY 5: Candidates for an AC ────────────────────────────────────────────
// Used by: candidate panel

MATCH (a:AssemblyConstituency {ac_id: $ac_id})
      -[:HAS_CANDIDATE_IN_ELECTION]->(c:Candidate)
      -[:REPRESENTS]->(p:Party)
RETURN
  c.candidate_id    AS candidate_id,
  c.name            AS name,
  p.name            AS party,
  c.criminal_cases  AS criminal_cases,
  c.serious_cases   AS serious_cases,
  c.total_assets    AS total_assets,
  c.total_liabilities AS total_liabilities,
  c.education       AS education,
  c.age             AS age
ORDER BY p.name;
```

```cypher
// ── QUERY 6: All booths for AC with pulse scores ─────────────────────────────
// Used by: AC overview map / table

MATCH (a:AssemblyConstituency {ac_id: $ac_id})-[:HAS_BOOTH]->(b:Booth)
OPTIONAL MATCH (b)<-[:MENTIONS_LOCATION]-(pe:PulseEvent)
WHERE pe.created_at >= datetime() - duration({days: 7})
  AND pe.entity IN ['BJP', 'SP', 'BSP']
WITH b,
     avg(CASE WHEN pe.entity = 'BJP' THEN pe.polarity * pe.confidence END) AS bjp_pulse,
     avg(CASE WHEN pe.entity IN ['SP','BSP','Congress'] THEN pe.polarity * pe.confidence END) AS opp_pulse,
     count(pe) AS event_count
RETURN
  b.booth_id              AS booth_id,
  b.booth_number          AS booth_number,
  b.polling_station_name  AS name,
  b.total_voters          AS total_voters,
  round(coalesce(bjp_pulse, 0.0) * 100) / 100  AS bjp_pulse,
  round(coalesce(opp_pulse, 0.0) * 100) / 100  AS opp_pulse,
  event_count
ORDER BY b.booth_number;
```

```cypher
// ── QUERY 7: Electoral roll summary for booth ────────────────────────────────
// Used by: booth demographics panel

MATCH (b:Booth {booth_id: $booth_id})
RETURN
  b.booth_id             AS booth_id,
  b.polling_station_name AS name,
  b.male_voters          AS male_voters,
  b.female_voters        AS female_voters,
  b.total_voters         AS total_voters,
  b.address              AS address;
```

```cypher
// ── QUERY 8: Panchayat governance context for a booth ───────────────────────
// Used by: governance tab (Week 2, but define now)

MATCH (b:Booth {booth_id: $booth_id})-[:LOCATED_IN]->(pan:Panchayat)
      -[:HAS_ACTIVITY]->(act:Activity)
RETURN
  pan.gp_name           AS panchayat,
  act.sector            AS sector,
  act.scheme_name       AS scheme,
  act.activity_desc     AS description,
  act.status            AS status
ORDER BY act.sector
LIMIT 10;
```

---

### 5.2 FastAPI Endpoints

```python
# api/main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .db import get_neo4j_session, get_pg_connection
from .queries import (
    get_booths_for_ac,
    get_booth_pulse,
    get_booth_issues,
    get_booth_comments,
    get_ac_candidates,
    get_booth_roll_summary,
)
from .schemas import BoothListResponse, BoothPulseResponse, IssueResponse

app = FastAPI(title="Gorakhpur KG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ENDPOINT 1 ───────────────────────────────────────────────────────────────
@app.get("/ac/{ac_id}/booths")
def list_booths(ac_id: str):
    """
    Returns all booths for the AC with latest pulse scores.
    Powers: sidebar dropdown + AC overview table.
    """
    rows = get_booths_for_ac(ac_id)
    if not rows:
        raise HTTPException(404, f"AC {ac_id} not found or has no booths")
    return {"ac_id": ac_id, "booths": rows, "count": len(rows)}


# ── ENDPOINT 2 ───────────────────────────────────────────────────────────────
@app.get("/booth/{booth_id}/pulse")
def booth_pulse(booth_id: str, days: int = Query(7, ge=1, le=90)):
    """
    Returns BJP vs opposition pulse score for a booth.
    Powers: pulse bar chart on booth profile page.
    """
    pulse = get_booth_pulse(booth_id, days=days)
    roll = get_booth_roll_summary(booth_id)
    return {
        "booth_id": booth_id,
        "pulse": pulse,                  # [{entity, pulse_score, event_count}]
        "roll_summary": roll,            # {male_voters, female_voters, total_voters}
        "window_days": days,
        "data_confidence": _compute_confidence(pulse),
    }

def _compute_confidence(pulse: list) -> str:
    total_events = sum(p.get("event_count", 0) for p in pulse)
    if total_events >= 100:   return "High"
    if total_events >= 20:    return "Medium"
    if total_events >= 5:     return "Low"
    return "Insufficient data"


# ── ENDPOINT 3 ───────────────────────────────────────────────────────────────
@app.get("/booth/{booth_id}/issues")
def booth_issues(booth_id: str, limit: int = Query(5, ge=1, le=10)):
    """
    Returns top issues by mention count with sentiment breakdown.
    Powers: issues radar/bar chart.
    """
    issues = get_booth_issues(booth_id, limit=limit)
    return {
        "booth_id": booth_id,
        "issues": issues,    # [{issue, mention_count, avg_polarity, neg/pos counts}]
    }


# ── ENDPOINT 4 ───────────────────────────────────────────────────────────────
@app.get("/booth/{booth_id}/comments")
def booth_comments(
    booth_id: str,
    limit: int = Query(10, ge=1, le=50),
    source: str = Query(None, description="Filter: youtube | news | all"),
):
    """
    Returns recent high-confidence pulse events (comments/news) for this booth.
    Powers: backing comments feed.
    """
    comments = get_booth_comments(booth_id, limit=limit, source=source)
    return {"booth_id": booth_id, "comments": comments}


# ── ENDPOINT 5 ───────────────────────────────────────────────────────────────
@app.get("/ac/{ac_id}/candidates")
def ac_candidates(ac_id: str):
    """
    Returns all candidates for the AC with affidavit summary.
    Powers: candidate panel.
    """
    candidates = get_ac_candidates(ac_id)
    return {"ac_id": ac_id, "candidates": candidates}


# ── ENDPOINT 6 (bonus) ───────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "gorakhpur-kg-api"}
```

```python
# api/queries.py  — wraps Cypher queries for FastAPI
from .db import get_neo4j_session
import functools

# Simple in-process cache for demo (not production-grade)
@functools.lru_cache(maxsize=128)
def get_booths_for_ac(ac_id: str) -> list[dict]:
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (a:AssemblyConstituency {ac_id: $ac_id})-[:HAS_BOOTH]->(b:Booth)
            OPTIONAL MATCH (b)<-[:MENTIONS_LOCATION]-(pe:PulseEvent)
            WHERE pe.created_at >= datetime() - duration({days: 7})
            WITH b,
                 avg(CASE WHEN pe.entity = 'BJP' THEN pe.polarity * pe.confidence END) AS bjp,
                 avg(CASE WHEN pe.entity IN ['SP','BSP','Congress'] THEN pe.polarity * pe.confidence END) AS opp,
                 count(pe) AS events
            RETURN b.booth_id AS booth_id, b.booth_number AS number,
                   b.polling_station_name AS name, b.total_voters AS total_voters,
                   round(coalesce(bjp,0.0)*100)/100 AS bjp_pulse,
                   round(coalesce(opp,0.0)*100)/100 AS opp_pulse,
                   events AS event_count
            ORDER BY b.booth_number
        """, ac_id=ac_id)
        return [dict(r) for r in result]


def get_booth_pulse(booth_id: str, days: int = 7) -> list[dict]:
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (b:Booth {booth_id: $booth_id})<-[:MENTIONS_LOCATION]-(pe:PulseEvent)
            WHERE pe.created_at >= datetime() - duration({days: $days})
              AND pe.entity IN ['BJP','SP','BSP','Congress']
            RETURN pe.entity AS entity,
                   round(avg(pe.polarity * pe.confidence)*100)/100 AS pulse_score,
                   count(*) AS event_count
            ORDER BY pulse_score DESC
        """, booth_id=booth_id, days=days)
        return [dict(r) for r in result]


def get_booth_issues(booth_id: str, limit: int = 5) -> list[dict]:
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (b:Booth {booth_id: $booth_id})<-[:MENTIONS_LOCATION]-(pe:PulseEvent)
                  -[:ABOUT_ISSUE]->(i:Issue)
            WHERE pe.created_at >= datetime() - duration({days: 30})
            RETURN i.name AS issue, count(pe) AS mention_count,
                   round(avg(pe.polarity)*100)/100 AS avg_polarity,
                   sum(CASE WHEN pe.polarity=-1 THEN 1 ELSE 0 END) AS negative_count,
                   sum(CASE WHEN pe.polarity=1 THEN 1 ELSE 0 END) AS positive_count
            ORDER BY mention_count DESC LIMIT $limit
        """, booth_id=booth_id, limit=limit)
        return [dict(r) for r in result]


def get_booth_comments(
    booth_id: str, limit: int = 10, source: str | None = None
) -> list[dict]:
    source_filter = "AND pe.source_type = $source" if source and source != "all" else ""
    with get_neo4j_session() as session:
        result = session.run(f"""
            MATCH (b:Booth {{booth_id: $booth_id}})<-[:MENTIONS_LOCATION]-(pe:PulseEvent)
            WHERE pe.final_confidence >= 0.6 {source_filter}
            RETURN pe.event_id AS id, pe.text_raw AS text,
                   pe.entity AS entity, pe.final_polarity AS polarity,
                   pe.issue AS issue, pe.final_confidence AS confidence,
                   pe.source_type AS source, toString(pe.created_at) AS created_at
            ORDER BY pe.created_at DESC LIMIT $limit
        """, booth_id=booth_id, limit=limit, source=source)
        return [dict(r) for r in result]


def get_ac_candidates(ac_id: str) -> list[dict]:
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (a:AssemblyConstituency {ac_id: $ac_id})
                  -[:HAS_CANDIDATE_IN_ELECTION]->(c:Candidate)
                  -[:REPRESENTS]->(p:Party)
            RETURN c.candidate_id AS id, c.name AS name, p.name AS party,
                   c.criminal_cases AS criminal_cases,
                   c.serious_cases AS serious_cases,
                   c.total_assets AS total_assets,
                   c.total_liabilities AS total_liabilities,
                   c.education AS education, c.age AS age
            ORDER BY p.name
        """, ac_id=ac_id)
        return [dict(r) for r in result]


def get_booth_roll_summary(booth_id: str) -> dict:
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (b:Booth {booth_id: $booth_id})
            RETURN b.male_voters AS male, b.female_voters AS female,
                   b.total_voters AS total
        """, booth_id=booth_id)
        row = result.single()
        return dict(row) if row else {}
```

---

## Section 6: Out-of-Scope for This 5-Day Sprint

### Explicitly Parked for Week 2+

| Item | Why Parked | When to Pick Up |
|---|---|---|
| MGNREGA / PMAY beneficiary data | Requires nregarep2 scraping + GP→booth fuzzy join — too much ETL for 5 days | Week 2, Day 8–10 |
| Jansunwai grievance portal | Portal access unpredictable, adds complex ETL | Week 2 |
| WhatsApp / SMS delivery integration | DLT registration takes 1–2 weeks; not needed for demo | Week 3 |
| IVR survey (Exotel/Knowlarity) | Setup requires vendor agreements | Week 4 |
| Voter-level hashed nodes | Legal review not complete; roll summary is enough for demo | Post legal clearance |
| VoterSegment targeting queries | Depends on voter nodes existing | Week 3 |
| Full panchayat governance layer | Only a 5–10 panchayat subset for demo richness | Week 2 |
| Field survey (KoBoToolbox) | Takes time to deploy field agents | Week 2 |
| BoothAgent / Karyakarta network | No agent data collected yet | Week 3 |
| Campierganj AC | Gorakhpur Urban only for pilot | Week 2 |
| GraphRAG natural language queries | LangChain+Neo4j setup adds complexity | Week 2 |
| PostGIS spatial clustering | Map works with booth-level pins, no clustering needed | Week 3 |
| Fine-tuned IndicBERT | Need 2000+ labeled examples first | Month 2 |
| Next.js React frontend | Streamlit is fine for demo | Post-demo decision |
| Redis / cache layer | `lru_cache` in FastAPI is enough for demo | Week 2 |
| Differential privacy | Not needed at demo scale | Pre-production |
| CI/CD GitHub Actions full pipeline | Basic `pytest` is enough for sprint | Week 2 |
| X/Twitter / Facebook ingestion | API costs + setup time | Week 3 |

### What the Demo WILL Show (and Must Work Perfectly)

```
✓  Select "Gorakhpur Urban" AC
✓  See list of 50–300 booths with basic pulse indicators
✓  Click any booth with data → see:
     - BJP vs Opposition pulse score (bar chart)
     - Top 3 issues with sentiment (bar chart)  
     - 5–10 backing comments (color-coded red/green)
     - Candidate panel: name, party, criminal cases, assets
     - Voter roll summary: M/F/Total
     - Data confidence indicator
✓  AC-level aggregate view when booth has insufficient data
✓  Demo runs live, not from screenshots
```

---

## Future Steps (Week 2–6 Roadmap)

```
Week 2:  Add Campierganj AC. Add eGramSwaraj full integration.
         Field surveys via KoBoToolbox. GraphRAG natural language queries.
         Redis caching. Historical election results in graph.

Week 3:  Voter nodes (post legal clearance). VoterSegment targeting.
         Booth agent network. Full panchayat layer.
         WhatsApp delivery (if DLT ready).

Week 4:  MGNREGA/PMAY scheme delivery layer.
         Jansunwai grievance integration.
         IVR survey integration.
         Caste/community dimension.

Week 5:  Fine-tune IndicBERT for sentiment (use 5-day sprint labels as seed).
         Spatial clustering (PostGIS + Kepler.gl map).
         Swing booth detection algorithm.
         Next.js dashboard upgrade.

Month 2: Scale to all Gorakhpur ACs.
         Automated daily pulse reports per AC via email/WhatsApp.
         Differential privacy on voter aggregates.
         Production hardening: monitoring, backups, access logs.
```
