# Gorakhpur Booth KG & Sentiment Engine — Master Plan
> Complete reference: data sources, environment, graph mapping, scraping, pipelines, and 15-person work distribution.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Data Sources — Full Catalogue](#2-data-sources--full-catalogue)
3. [Environment & Tech Stack Requirements](#3-environment--tech-stack-requirements)
4. [Data Source → Neo4j Graph Mapping](#4-data-source--neo4j-graph-mapping)
5. [Web Scraping Plan — Source by Source](#5-web-scraping-plan--source-by-source)
6. [ETL & Orchestration Architecture](#6-etl--orchestration-architecture)
7. [Multilingual NLP & Sentiment Pipeline](#7-multilingual-nlp--sentiment-pipeline)
8. [Knowledge Graph Build Plan](#8-knowledge-graph-build-plan)
9. [Analytics, Aggregation & Dashboard](#9-analytics-aggregation--dashboard)
10. [Messaging & Targeting Layer](#10-messaging--targeting-layer)
11. [Security & Compliance](#11-security--compliance)
12. [15-Person Work Distribution — Step by Step](#12-15-person-work-distribution--step-by-step)
13. [Project Timeline](#13-project-timeline)

---

## 1. Project Overview

### What we are building
A **booth-level political intelligence system** for Gorakhpur, UP that:
- Maps the full election geography: State → District → Assembly Constituency → Booth → Panchayat → Village
- Builds a living voter knowledge graph with demographic and scheme touchpoints
- Continuously ingests and analyses public digital signals (YouTube, news, social)
- Runs a deterministic multilingual (Hindi / Bhojpuri / English) sentiment pipeline
- Computes booth-level pulse scores and issue rankings
- Supports hyper-local governance messaging to voter segments

### Pilot Scope
- **District:** Gorakhpur, Uttar Pradesh
- **Phase 1 AC:** Gorakhpur Urban (1 AC, ~300 booths)
- **Phase 2 AC:** Add Campierganj
- **Timeline:** 5 weeks to stable v1

### Architecture Layers
```
L0  Infrastructure & Security
L1  Data Collection (scraping, APIs, field)
L2  ETL & Data Quality
L3  Multilingual NLP Pipeline
L4  Knowledge Graph (Neo4j)
L5  Analytics & Aggregation
L6  API & Delivery
L7  Visualization & Analyst Console
```

---

## 2. Data Sources — Full Catalogue

### 2.1 Official / Structured Sources

#### SOURCE-01: ECI / CEO Uttar Pradesh — Booth & AC Master
- **What it contains:** List of all Assembly Constituencies in Gorakhpur district, polling station (booth) names, addresses, BLO (Booth Level Officer) names and contacts, AC-wise booth count.
- **URL:** `https://ceouttarpradesh.nic.in/` → Constituency → Assembly Constituency Polling Stations
- **Format:** HTML tables, downloadable PDFs
- **How we use it:** This is the foundation. Every other data source maps back to a `booth_id` from here.
- **Priority:** P0 — must be done first, everything else depends on it
- **Output tables:** `ac_master`, `booth_master`, `blo_master`

#### SOURCE-02: ECI Candidate Lists & Affidavits (via MyNeta / ADR)
- **What it contains:** Candidate names, parties, criminal cases, serious criminal cases, total assets, total liabilities, education qualification, profession, age.
- **URL:** `https://myneta.info/uttar-pradesh/` and `https://affidavit.eci.gov.in/`
- **Format:** HTML tables + linked PDF affidavits
- **How we use it:** Populate candidate profiles. Feed into the `Candidate` node in Neo4j. Used in dashboard candidate panel.
- **Priority:** P0
- **Output tables:** `candidate_master`, `candidate_affidavits`

#### SOURCE-03: Electoral Roll Data
- **What it contains:** Voter name, EPIC number, gender, age, address, part number (booth), serial number within part.
- **URL:** `https://ceouttarpradesh.nic.in/` → Electoral Rolls (PDFs per booth/part)
- **Format:** PDF (scanned or searchable), some accessible via Voter Helpline API
- **Legal note:** Electoral rolls are public documents but usage is restricted under RPA 1951 — only for election purposes. Must get legal sign-off before bulk processing.
- **How we use it:** We do NOT store raw voter data in Neo4j. We generate:
  - `electoral_roll_summary` (aggregated counts per booth: male/female/total)
  - Hashed `Voter` nodes with only `age_band`, `gender`, `booth_id` — no names, no EPIC
- **Priority:** P1
- **Output tables:** `electoral_roll_raw` (secure, restricted), `electoral_roll_summary`

#### SOURCE-04: ECI Historical Election Results
- **What it contains:** AC-wise and booth-wise vote counts per party and candidate for past elections (2022 UP Assembly, 2024 Lok Sabha, 2017 UP Assembly).
- **URL:** `https://results.eci.gov.in/` — Results archives
- **Format:** HTML tables, Excel downloads
- **How we use it:** Baseline performance data. `Candidate–[:WON_IN / :LOST_IN]→Election` with vote share and margin.
- **Priority:** P1
- **Output tables:** `election_results(ac_id, election_year, candidate_id, party, votes, vote_share, margin, result)`

#### SOURCE-05: eGramSwaraj — Panchayat Activities & Schemes
- **What it contains:** Panchayat-level development works: roads, wells, toilets, hand pumps, MGNREGA jobs, PMAY houses, scheme beneficiary counts by GP.
- **URL:** `https://egramswaraj.gov.in/` → Know Your Panchayat / Work Reports
- **Format:** HTML tables, CSV/Excel exports
- **How we use it:** Governance ground truth. Links panchayat development activity to booths. Used to assess scheme delivery vs. grievances.
- **Priority:** P1
- **Output tables:** `panchayat_master`, `village_master`, `panchayat_activity`

#### SOURCE-06: MGNREGA Beneficiary Data
- **What it contains:** Job card holders, workdays provided, wages paid, active workers — at GP level.
- **URL:** `https://nregarep2.nic.in/netnrega/` → District → Block → GP reports
- **Format:** HTML tables
- **How we use it:** Scheme touchpoint data. "How many voters in this panchayat received MGNREGA wages?" Feeds `SchemeBenefitEvent` nodes.
- **Priority:** P2
- **Output tables:** Merged into `panchayat_activity` with `scheme_name = MGNREGA`

#### SOURCE-07: PMAY-G Beneficiary Data
- **What it contains:** Pradhan Mantri Awas Yojana (rural) beneficiaries by GP, sanctioned vs completed houses.
- **URL:** `https://pmayg.nic.in/` → Reports → GP-wise beneficiaries
- **Format:** HTML tables
- **How we use it:** Same as MGNREGA — scheme delivery indicator at panchayat level.
- **Priority:** P2

#### SOURCE-08: Jansunwai (UP Grievance Portal)
- **What it contains:** Public citizen grievances filed with the UP government, categorised by department and district.
- **URL:** `https://jansunwai.up.nic.in/`
- **Format:** HTML tables (public-facing summary), open data where available
- **How we use it:** Issue signal. "What are people in Gorakhpur complaining about?" Maps to `Grievance` and `Issue` nodes.
- **Priority:** P2
- **Output tables:** `grievances(grievance_id, district, block, category, sub_category, status, date_filed)`

---

### 2.2 Dynamic / Digital Signal Sources

#### SOURCE-09: YouTube — Local Political Videos & Comments
- **What it contains:** Comments on political YouTube channels covering Gorakhpur (local news channels, politician channels, public rallies).
- **Tool:** `yt-dlp` for metadata + comments; YouTube Data API v3 for structured access
- **How to identify channels:** Search YouTube for "गोरखपुर चुनाव", "gorakhpur BJP", "gorakhpur SP", local channels like "Gorakhpur News", politician-specific channels.
- **How we use it:** Primary source of public sentiment. Comments are in Hindi/Bhojpuri/English mixed. Run through full NLP pipeline.
- **Priority:** P1
- **Output tables:** `yt_channels`, `yt_videos`, `yt_comments`
- **Volume estimate:** 50–200 videos, 10,000–50,000 comments for pilot

#### SOURCE-10: Local News Portals — Hindi Digital News
- **What it contains:** News articles about Gorakhpur politics, governance, development, crime.
- **Sources:**
  - Jagran: `https://www.jagran.com/uttar-pradesh/gorakhpur.html`
  - Amar Ujala: `https://www.amarujala.com/uttar-pradesh/gorakhpur`
  - Navbharat Times: `https://navbharattimes.indiatimes.com/state/uttar-pradesh/gorakhpur`
  - Local portals: `gorakhpurnewsline.com`, `gorakhpurpost.com`
- **Format:** HTML articles
- **How we use it:** Issue detection and sentiment at district/AC level. Geographic mentions extracted for booth mapping.
- **Priority:** P1
- **Output tables:** `news_articles(article_id, source, headline, body, published_at, url, ac_hint, booth_hint)`

#### SOURCE-11: WhatsApp Public Groups / Forwarded Content
- **What it contains:** Political messages, memes, audio clips forwarded in local WhatsApp groups.
- **How to collect:** Manual monitoring by field agents; WhatsApp Web scraping (within terms of service limits); public Telegram mirrors.
- **Legal note:** Be careful — only use content from public groups or with explicit consent.
- **How we use it:** Captures grassroots narrative that doesn't appear on YouTube/news. Bhojpuri content is heavy here.
- **Priority:** P3
- **Output tables:** `social_posts` (same table, `platform = 'whatsapp'`)

#### SOURCE-12: X (Twitter) / Facebook (Optional)
- **What it contains:** Tweets and posts from local politicians, party handles, journalists.
- **How to collect:** X Basic API (free tier: 500k tweets/month read), Facebook Graph API (limited public data)
- **How we use it:** Politician messaging tracking. What are candidates saying? What are party handles amplifying?
- **Priority:** P3
- **Output tables:** `social_posts`

---

### 2.3 Field / Primary Data Sources

#### SOURCE-13: Field Surveys (KoBoToolbox Forms)
- **What it contains:** Structured responses from ground surveys — voter sentiment, issues, candidate preference, scheme awareness.
- **Tool:** KoBoToolbox (free, open-source, works offline)
- **How to collect:** 15–20 field agents per AC, 20–50 surveys per booth per wave
- **How we use it:** Highest-quality ground-truth sentiment. Directly creates `PulseEvent` nodes with `source_type = 'survey'` and `geo_confidence = high`.
- **Priority:** P1
- **Output tables:** `survey_responses`, then normalized into `pulse_events`

#### SOURCE-14: Booth Agent (Karyakarta) Reports
- **What it contains:** Subjective intel from party booth workers — attendance at events, local mood, key influencers, issues in their ward.
- **How to collect:** Simple WhatsApp form or Google Form submitted by booth workers daily/weekly
- **How we use it:** `BoothAgent` node in Neo4j. Their reports create `PulseEvent` nodes with qualitative notes.
- **Priority:** P2

#### SOURCE-15: IVR Survey Responses
- **What it contains:** Automated phone survey responses — numeric keypad choices on issues and candidate preference.
- **Tool:** Exotel or Knowlarity (IVR platforms, have free/trial tiers)
- **How we use it:** Reaches non-smartphone voters. Adds to `pulse_events` with `source_type = 'ivr'`.
- **Priority:** P3

---

## 3. Environment & Tech Stack Requirements

### 3.1 Local Development Machine (each engineer)
```
OS:         Ubuntu 22.04 / Windows 11 + WSL2 / macOS
Python:     3.11+
RAM:        Minimum 16GB (for local Neo4j + PostgreSQL + Python)
Storage:    50GB free (PDFs, raw data, model weights)
GPU:        Optional (for local IndicBERT fine-tuning)
```

### 3.2 Shared Infrastructure (set up by Person 2)

#### Option A — Local / On-Premises (low cost, full control)
```
Server:       1x Ubuntu 22.04 VM (16 cores, 64GB RAM, 500GB SSD)
              Can use any cloud VM: AWS t3.2xlarge, GCP n2-standard-8, or local server
Database:     PostgreSQL 16 + pgvector extension
Graph:        Neo4j 5.x Community (free) or AuraDB Free tier (5GB)
Cache:        Redis 7.x
Orchestration: Prefect 3.x (self-hosted server OR free Prefect Cloud)
Object Storage: MinIO (self-hosted S3 compatible) OR AWS S3 free tier
```

#### Option B — Cloud (easier team collaboration)
```
PostgreSQL:  Neon.tech (free tier, 10GB) or Supabase (free tier)
Neo4j:       AuraDB Free (5GB graph) — sufficient for pilot
Redis:       Upstash Redis (free tier, serverless)
Orchestration: Prefect Cloud (free tier: 3 workspaces, unlimited runs)
Storage:     AWS S3 (5GB free tier) or Cloudflare R2 (10GB free)
API:         Railway.app or Render.com (free tier for FastAPI)
Dashboard:   Streamlit Community Cloud (free)
```

**Recommendation: Use Option B for the pilot** — zero infra management, team can collaborate from Day 1.

### 3.3 Python Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Core dependencies
pip install \
  # Data collection
  playwright beautifulsoup4 requests httpx yt-dlp pdfplumber pytesseract \
  # Data processing
  pandas numpy sqlalchemy psycopg2-binary alembic \
  # NLP & Language
  langdetect fasttext indic-nlp-library thefuzz \
  sentence-transformers torch transformers \
  # LLM & Extraction
  groq google-generativeai instructor pydantic \
  # Graph
  neo4j py2neo \
  # Orchestration
  prefect \
  # API
  fastapi uvicorn \
  # Dashboard
  streamlit plotly folium \
  # Utils
  python-dotenv loguru great-expectations
```

### 3.4 Environment Variables (.env)
```env
# Database
POSTGRES_URL=postgresql://user:pass@host:5432/gorakhpur_db
REDIS_URL=redis://localhost:6379

# Graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_AURA_URI=neo4j+s://xxxx.databases.neo4j.io  # if using AuraDB

# LLM APIs
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key

# Translation
BHASHINI_API_KEY=your_bhashini_key
BHASHINI_USER_ID=your_user_id

# YouTube
YOUTUBE_API_KEY=your_yt_api_key

# Monitoring
PREFECT_API_URL=https://api.prefect.cloud/api/accounts/...
PREFECT_API_KEY=your_prefect_key
```

### 3.5 Database Schema Setup

```sql
-- Run once on fresh PostgreSQL instance
CREATE EXTENSION IF NOT EXISTS vector;      -- for pgvector semantic search
CREATE EXTENSION IF NOT EXISTS postgis;     -- for geo-spatial queries
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- for fuzzy text matching
```

### 3.6 Neo4j Setup Constraints & Indexes

```cypher
-- Run once after Neo4j is up
CREATE CONSTRAINT FOR (b:Booth) REQUIRE b.booth_id IS UNIQUE;
CREATE CONSTRAINT FOR (a:AssemblyConstituency) REQUIRE a.ac_id IS UNIQUE;
CREATE CONSTRAINT FOR (c:Candidate) REQUIRE c.candidate_id IS UNIQUE;
CREATE CONSTRAINT FOR (v:Voter) REQUIRE v.voter_uid IS UNIQUE;
CREATE CONSTRAINT FOR (p:Panchayat) REQUIRE p.panchayat_id IS UNIQUE;
CREATE CONSTRAINT FOR (e:PulseEvent) REQUIRE e.event_id IS UNIQUE;

CREATE INDEX FOR (b:Booth) ON (b.ac_id);
CREATE INDEX FOR (p:PulseEvent) ON (p.mapped_booth_id);
CREATE INDEX FOR (p:PulseEvent) ON (p.issue);
CREATE INDEX FOR (v:Voter) ON (v.age_band, v.gender);
```

---

## 4. Data Source → Neo4j Graph Mapping

### 4.1 Full Mapping Table

| Data Source | Raw Table(s) | Neo4j Node(s) Created | Neo4j Relationships Created |
|---|---|---|---|
| SOURCE-01 ECI Booths | `ac_master`, `booth_master`, `blo_master` | `State`, `District`, `AssemblyConstituency`, `Booth` | `HAS_DISTRICT`, `HAS_AC`, `HAS_BOOTH` |
| SOURCE-02 Affidavits | `candidate_master`, `candidate_affidavits` | `Candidate`, `Party`, `Election` | `REPRESENTS`, `CONTESTS_IN`, `HAS_CANDIDATE_IN_ELECTION` |
| SOURCE-03 Electoral Rolls | `electoral_roll_summary` | `Voter` (hashed), `VoterSegment` | `HAS_VOTER`, `BELONGS_TO_SEGMENT` |
| SOURCE-04 Historical Results | `election_results` | `Election` (update existing) | `WON_IN`, `LOST_IN` with `{votes, vote_share, margin}` |
| SOURCE-05 eGramSwaraj | `panchayat_master`, `panchayat_activity` | `Panchayat`, `Village`, `Activity`, `Scheme` | `LOCATED_IN`, `HAS_ACTIVITY`, `OF_SCHEME` |
| SOURCE-06 MGNREGA | merged into `panchayat_activity` | `SchemeBenefitEvent` | `RECEIVED_BENEFIT`, `OF_SCHEME` |
| SOURCE-07 PMAY-G | merged into `panchayat_activity` | `SchemeBenefitEvent` | `RECEIVED_BENEFIT`, `OF_SCHEME` |
| SOURCE-08 Jansunwai | `grievances` | `Grievance`, `Issue` | `RAISED_GRIEVANCE`, `ABOUT_ISSUE` |
| SOURCE-09 YouTube | `yt_comments` → `pulse_events` | `PulseEvent` | `ABOUT_ISSUE`, `TARGETS`, `MENTIONS_LOCATION` |
| SOURCE-10 News | `news_articles` → `pulse_events` | `PulseEvent` | `ABOUT_ISSUE`, `TARGETS`, `MENTIONS_LOCATION` |
| SOURCE-13 Field Surveys | `survey_responses` → `pulse_events` | `PulseEvent` | `ABOUT_ISSUE`, `TARGETS`, `MENTIONS_LOCATION` |
| SOURCE-14 Booth Agents | `agent_reports` → `pulse_events` | `BoothAgent`, `PulseEvent` | `REPORTS_FOR`, `ABOUT_ISSUE` |
| Aggregation Jobs | `booth_metrics` | Relationship properties | `HAS_AGGREGATE_SENTIMENT {score, window, issue}` |
| Messaging Layer | `messages` | `Message`, `Channel` | `TARGETED_WITH`, `VIA` |

### 4.2 Graph Schema Diagram (Text)

```
State (UP)
  └─[:HAS_DISTRICT]→ District (Gorakhpur)
       └─[:HAS_AC]→ AssemblyConstituency (Gorakhpur Urban)
            └─[:HAS_BOOTH]→ Booth (Booth #1..#300)
                 │
                 ├─[:LOCATED_IN]→ Panchayat/Ward
                 │                    └─[:HAS_VILLAGE]→ Village
                 │                    └─[:HAS_ACTIVITY]→ Activity → [:OF_SCHEME]→ Scheme
                 │
                 ├─[:HAS_VOTER]→ Voter (hashed_uid, age_band, gender)
                 │                    └─[:BELONGS_TO_SEGMENT]→ VoterSegment
                 │                    └─[:RECEIVED_BENEFIT]→ SchemeBenefitEvent → [:OF_SCHEME]→ Scheme
                 │                    └─[:RAISED_GRIEVANCE]→ Grievance → [:ABOUT_ISSUE]→ Issue
                 │
                 ├─[:HAS_CANDIDATE_IN_ELECTION]→ Candidate
                 │                                    └─[:REPRESENTS]→ Party
                 │                                    └─[:CONTESTS_IN]→ Election
                 │
                 └─[:HAS_AGGREGATE_SENTIMENT {issue, score, window}]→ Issue

PulseEvent (sentiment unit)
  ├─[:ABOUT_ISSUE]→ Issue
  ├─[:TARGETS]→ Party | Candidate
  └─[:MENTIONS_LOCATION]→ Booth | Panchayat | AssemblyConstituency

VoterSegment
  └─[:TARGETED_WITH {sent_at}]→ Message
       └─[:VIA]→ Channel

BoothAgent
  └─[:REPORTS_FOR]→ Booth
  └─[:AFFILIATED_WITH]→ Party
```

### 4.3 Node Property Definitions

```
Booth {
  booth_id: string (PK),
  booth_number: int,
  polling_station_name: string,
  address: string,
  ac_id: string,
  locality_hint: string,
  lat: float, lon: float,
  male_voters: int, female_voters: int, total_voters: int
}

Candidate {
  candidate_id: string,
  name: string, name_hi: string,
  party: string, ac_id: string,
  criminal_cases: int, serious_cases: int,
  total_assets: bigint, total_liabilities: bigint,
  education: string, profession: string, age: int
}

PulseEvent {
  event_id: string,
  source_type: enum[youtube|news|survey|field_note|ivr|social],
  source_id: string,
  entity: string, entity_type: enum[party|candidate|scheme|issue|govt],
  issue: string,
  polarity: int (-1 | 0 | 1),
  confidence: float,
  language: string,
  location_text: string,
  mapped_booth_id: string,
  mapped_ac_id: string,
  geo_confidence: float,
  created_at: datetime
}

VoterSegment {
  segment_id: string,
  booth_id: string,
  age_band: string (18-25|26-35|36-50|51+),
  gender: string,
  top_issue: string,
  scheme_aware: boolean,
  approx_count: int
}
```

---

## 5. Web Scraping Plan — Source by Source

### 5.1 ECI / CEO UP — Booths & ACs (SOURCE-01)

**Target URLs:**
- AC List: `https://ceouttarpradesh.nic.in/constituency/ACDetails.aspx`
- Booth List per AC: `https://ceouttarpradesh.nic.in/BLO/BLODetails.aspx`

**Tool:** `Playwright` (handles JavaScript-rendered pages) + `BeautifulSoup4`

**Step-by-step scraping logic:**
```python
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd

def scrape_ac_list():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://ceouttarpradesh.nic.in/constituency/ACDetails.aspx")
        # Filter by district = Gorakhpur
        page.select_option("#ddlDistrict", label="Gorakhpur")
        page.click("#btnSearch")
        page.wait_for_selector("table#GridView1")
        html = page.content()
        browser.close()
    
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "GridView1"})
    rows = table.find_all("tr")[1:]  # skip header
    acs = []
    for row in rows:
        cols = row.find_all("td")
        acs.append({
            "ac_id": cols[0].text.strip(),
            "ac_name": cols[1].text.strip(),
            "ac_type": cols[2].text.strip(),   # Urban/Rural
            "district": "Gorakhpur"
        })
    return pd.DataFrame(acs)
```

**Handling PDFs (booth address lists):**
```python
import pdfplumber

def parse_booth_pdf(pdf_path):
    booths = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table[1:]:  # skip header
                    booths.append({
                        "booth_number": row[0],
                        "polling_station_name": row[1],
                        "address": row[2],
                        "male_voters": row[3],
                        "female_voters": row[4],
                        "total_voters": row[5]
                    })
    return booths
```

**Rate limiting:** Add `time.sleep(2)` between requests. CEO UP blocks rapid requests.

---

### 5.2 MyNeta — Candidate Affidavits (SOURCE-02)

**Target URL pattern:** `https://myneta.info/uttar-pradesh-assembly-2022/constituency.php?constituency_id=XXX`

**Tool:** `requests` + `BeautifulSoup4`

**Step-by-step:**
```python
import requests
from bs4 import BeautifulSoup

GORAKHPUR_AC_IDS = {
    "gorakhpur_urban": 238,
    "campierganj": 240,
    # ... add all Gorakhpur ACs
}

def scrape_candidates(ac_id: int):
    url = f"https://myneta.info/uttar-pradesh-assembly-2022/constituency.php?constituency_id={ac_id}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    
    candidates = []
    table = soup.find("table", class_="w3-table-all")
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        affidavit_url = cols[1].find("a")["href"] if cols[1].find("a") else None
        candidates.append({
            "name": cols[1].text.strip(),
            "party": cols[2].text.strip(),
            "criminal_cases": cols[3].text.strip(),
            "serious_cases": cols[4].text.strip(),
            "total_assets": cols[5].text.strip(),
            "total_liabilities": cols[6].text.strip(),
            "education": cols[7].text.strip(),
            "affidavit_url": affidavit_url
        })
    return candidates

def parse_affidavit_pdf(pdf_url):
    # Download and parse PDF using pdfplumber
    resp = requests.get(pdf_url)
    with open("/tmp/affidavit.pdf", "wb") as f:
        f.write(resp.content)
    # Use pdfplumber to extract structured fields
    ...
```

---

### 5.3 ECI Historical Results (SOURCE-04)

**Target URL:** `https://results.eci.gov.in/ResultAcGenMar2022/`

**Tool:** `requests` + `BeautifulSoup4` + optional Excel download

```python
def scrape_ac_results(state="U05", ac_number="238"):
    # ECI results URL pattern
    url = f"https://results.eci.gov.in/ResultAcGenMar2022/candidateswise-{state}{ac_number.zfill(3)}.htm"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    results = []
    table = soup.find("table", id="tblData")
    for row in table.find_all("tr")[2:]:  # skip two header rows
        cols = row.find_all("td")
        results.append({
            "candidate_name": cols[1].text.strip(),
            "party": cols[2].text.strip(),
            "evm_votes": cols[3].text.strip(),
            "postal_votes": cols[4].text.strip(),
            "total_votes": cols[5].text.strip(),
            "result": cols[6].text.strip()  # WON/LOST
        })
    return results
```

---

### 5.4 eGramSwaraj — Panchayat Data (SOURCE-05)

**Target URLs:**
- Know Your Panchayat: `https://egramswaraj.gov.in/knowYourPanchayat.do`
- Work Reports: `https://egramswaraj.gov.in/`

**Tool:** `requests` + `BeautifulSoup4` (mostly server-rendered)

```python
def scrape_panchayat_profile(state="UP", district="Gorakhpur", block_name="Gorakhpur"):
    # eGramSwaraj uses POST forms with dropdown selections
    session = requests.Session()
    # Step 1: Get state/district codes
    # Step 2: POST to get block list
    # Step 3: POST to get GP list
    # Step 4: For each GP, get profile and activity data
    ...
```

**Note:** eGramSwaraj has a public API for some data. Check `https://egramswaraj.gov.in/api/` for JSON endpoints — faster than scraping HTML.

---

### 5.5 YouTube Comments (SOURCE-09)

**Method A — yt-dlp (no API key needed):**
```bash
# Get video IDs for a channel
yt-dlp --get-id "https://www.youtube.com/@GorakhpurNewsChannel" --playlist-end 50

# Get comments for a video
yt-dlp --write-comments --skip-download -o "%(id)s" "https://www.youtube.com/watch?v=VIDEO_ID"
# This writes VIDEO_ID.info.json with comments array
```

```python
import yt_dlp
import json

def fetch_video_comments(video_url: str):
    ydl_opts = {
        "writecomments": True,
        "skip_download": True,
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
    
    comments = []
    for c in info.get("comments", []):
        comments.append({
            "comment_id": c["id"],
            "author": c["author"],
            "text": c["text"],
            "like_count": c.get("like_count", 0),
            "published_at": c["timestamp"]
        })
    return comments
```

**Method B — YouTube Data API v3 (10,000 units/day free):**
```python
from googleapiclient.discovery import build

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def search_gorakhpur_videos():
    request = youtube.search().list(
        q="गोरखपुर चुनाव BJP SP",
        part="id,snippet",
        type="video",
        regionCode="IN",
        relevanceLanguage="hi",
        maxResults=50
    )
    return request.execute()

def get_video_comments(video_id: str, max_comments=500):
    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        order="relevance"
    )
    # Paginate with nextPageToken
    ...
```

**Which channels to target:**
- News: "Gorakhpur News", "UP Tak", "TV9 Bharatvarsh UP"
- Political: CM Yogi's official channel, opposition channels
- Local influencers: Search `gorakhpur site:youtube.com` to find

---

### 5.6 News Portals (SOURCE-10)

**Jagran Gorakhpur:**
```python
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def scrape_jagran_gorakhpur(days_back=7):
    base_url = "https://www.jagran.com/uttar-pradesh/gorakhpur.html"
    articles = []
    
    resp = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    
    for article_div in soup.find_all("div", class_="jagran-story"):
        title = article_div.find("h2").text.strip()
        link = article_div.find("a")["href"]
        date_str = article_div.find("span", class_="date").text.strip()
        
        # Fetch full article body
        article_resp = requests.get(link)
        article_soup = BeautifulSoup(article_resp.text, "html.parser")
        body = article_soup.find("div", class_="article-content").get_text()
        
        articles.append({
            "title": title, "url": link,
            "body": body, "published_at": date_str,
            "source": "jagran"
        })
    return articles
```

**Generic news scraper pattern:**
```python
# Use newspaper3k for easy article extraction
from newspaper import Article

def extract_article(url: str):
    article = Article(url, language="hi")
    article.download()
    article.parse()
    return {
        "title": article.title,
        "body": article.text,
        "published_at": article.publish_date,
        "authors": article.authors
    }
```

---

### 5.7 Scraping Best Practices for this Project

```python
import time
import random
from functools import wraps

# Polite scraper — always add delays
def polite_request(url, min_delay=2, max_delay=5):
    time.sleep(random.uniform(min_delay, max_delay))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "hi-IN,hi;q=0.9,en-IN;q=0.8"
    }
    return requests.get(url, headers=headers, timeout=30)

# Retry decorator for flaky government websites
def retry(max_attempts=3, delay=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (attempt + 1))
        return wrapper
    return decorator
```

---

## 6. ETL & Orchestration Architecture

### 6.1 Why Prefect (not Airflow)

Airflow is free but operationally heavy — needs its own PostgreSQL, Redis, and multiple processes. For a 15-person team building product, not infrastructure, **Prefect 3** is better:
- `pip install prefect` and `prefect server start` — that's it
- Free Prefect Cloud dashboard for the whole team
- Same Python code runs locally and in production
- Built-in retry, logging, alerting

### 6.2 Prefect Flow Structure

```
flows/
  ├── official_data/
  │   ├── flow_eci_booths.py         → scrapes + loads booth_master
  │   ├── flow_candidates.py         → scrapes + loads candidate_master
  │   ├── flow_electoral_rolls.py    → parses PDFs + loads roll_summary
  │   └── flow_egramswaraj.py        → scrapes + loads panchayat data
  │
  ├── dynamic_signals/
  │   ├── flow_youtube.py            → fetches new comments every 6h
  │   ├── flow_news.py               → crawls news portals every 6h
  │   └── flow_field_surveys.py      → pulls KoBoToolbox submissions hourly
  │
  ├── nlp/
  │   ├── flow_language_detect.py    → language detection + Bhashini normalization
  │   └── flow_sentiment_extract.py  → LLM extraction + rule fallback + geo resolution
  │
  ├── graph/
  │   ├── flow_load_structure.py     → loads geo hierarchy into Neo4j
  │   ├── flow_load_voters.py        → loads hashed voter nodes
  │   └── flow_load_pulse.py         → loads pulse_events into Neo4j
  │
  └── aggregation/
      └── flow_booth_metrics.py      → computes booth_metrics every 6h
```

### 6.3 Prefect Deployment Schedule

```python
from prefect import serve
from flows.official_data.flow_eci_booths import eci_booths_flow
from flows.dynamic_signals.flow_youtube import youtube_flow
from flows.nlp.flow_sentiment_extract import sentiment_flow
from flows.aggregation.flow_booth_metrics import metrics_flow

if __name__ == "__main__":
    serve(
        eci_booths_flow.to_deployment("eci-booths", cron="0 6 * * 1"),     # Monday 6am
        youtube_flow.to_deployment("youtube-ingest", cron="0 */6 * * *"),  # every 6h
        sentiment_flow.to_deployment("sentiment", cron="30 */6 * * *"),    # offset 30m
        metrics_flow.to_deployment("metrics", cron="0 */6 * * *"),         # every 6h
    )
```

### 6.4 PostgreSQL Table DDL (Key Tables)

```sql
-- Core master tables
CREATE TABLE ac_master (
    ac_id VARCHAR(20) PRIMARY KEY,
    ac_name VARCHAR(100), ac_type VARCHAR(20),
    district_id VARCHAR(20), district_name VARCHAR(50)
);

CREATE TABLE booth_master (
    booth_id VARCHAR(30) PRIMARY KEY,
    ac_id VARCHAR(20) REFERENCES ac_master(ac_id),
    booth_number INT,
    polling_station_name TEXT,
    address TEXT,
    locality_hint VARCHAR(200),
    lat DECIMAL(10,7), lon DECIMAL(10,7),
    male_voters INT, female_voters INT, other_voters INT, total_voters INT
);

-- Pulse events (central table for all sentiment data)
CREATE TABLE pulse_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(30),   -- youtube|news|survey|field_note|ivr
    source_id VARCHAR(100),
    text_raw TEXT,
    text_normalized_hi TEXT,   -- Bhashini-normalized Hindi
    entity VARCHAR(100),
    entity_type VARCHAR(30),
    issue VARCHAR(50),
    polarity SMALLINT,         -- -1, 0, 1
    confidence FLOAT,
    language VARCHAR(10),
    location_text VARCHAR(200),
    mapped_booth_id VARCHAR(30),
    mapped_ac_id VARCHAR(20),
    mapped_panchayat_id VARCHAR(30),
    geo_confidence FLOAT,
    llm_output JSONB,          -- raw LLM JSON for audit
    rule_output JSONB,         -- rule-based output for comparison
    final_polarity SMALLINT,   -- policy-chosen final value
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Aggregated booth metrics
CREATE TABLE booth_metrics (
    booth_id VARCHAR(30),
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    bjp_pulse_score FLOAT,
    opp_pulse_score FLOAT,
    pain_index FLOAT,
    top_issue VARCHAR(50),
    issue_breakdown JSONB,     -- {water: 0.3, roads: 0.2, ...}
    women_empowerment_index FLOAT,
    data_confidence FLOAT,
    event_count INT,
    PRIMARY KEY (booth_id, window_start)
);
```

---

## 7. Multilingual NLP & Sentiment Pipeline

### 7.1 Pipeline Flow (per text item)

```
Raw text (Hindi/Bhojpuri/English/mixed)
    │
    ▼
[Stage 1] Language Detection
    Using: langdetect + fastText model
    Output: language code (hi | bho | en | mix)
    │
    ▼
[Stage 2] Text Cleaning
    - Remove URLs, usernames (@), hashtags
    - Normalize Unicode (NFC)
    - Transliterate Romanized Hindi → Devanagari
    - Strip repeated characters (e.g. "achhaaa" → "achha")
    │
    ▼
[Stage 3] Dialect Translation (if bho or mix)
    Primary: Bhashini API (POST to translation endpoint)
    Fallback: IndicTrans2 local model (if Bhashini fails)
    Output: normalized_hi (standard Hindi)
    │
    ▼
[Stage 4A] LLM Extraction (Groq/Gemini + Instructor)
    Input: normalized_hi
    Output: List[SentimentStatement] (Pydantic schema)
    Fields: entity, entity_type, issue, polarity, confidence, location_mention
    │
    ▼
[Stage 4B] Rule-Based Fallback
    Triggers when: confidence < 0.6 OR LLM schema error
    Uses: Political lexicon (party aliases, issue terms, sentiment phrases)
    │
    ▼
[Stage 5] Caste/Community Tagging (Custom NER)
    Identify: caste group mentions, community-specific issues
    Uses: Custom NER model or regex patterns
    │
    ▼
[Stage 6] Geo-Entity Resolution
    Extract location_mention from LLM output
    Fuzzy match against: booth names, panchayat names, village names, ward names
    Use: thefuzz (Levenshtein) for exact, IndicBERT embeddings for semantic
    Output: mapped_booth_id, geo_confidence
    │
    ▼
[Stage 7] Persist
    Write to: pulse_events table (PostgreSQL)
    Async write to: PulseEvent node (Neo4j)
```

### 7.2 LLM Extraction Schema

```python
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class EntityType(str, Enum):
    PARTY = "party"
    CANDIDATE = "candidate"
    SCHEME = "scheme"
    ISSUE = "issue"
    GOVT = "govt"

class IssueType(str, Enum):
    WATER = "water"
    ROADS = "roads"
    ELECTRICITY = "electricity"
    JOBS = "jobs"
    WOMEN_SAFETY = "women_safety"
    PRICE_RISE = "price_rise"
    FARMER = "farmer"
    SUGARCANE = "sugarcane"
    HEALTH = "health"
    EDUCATION = "education"
    CORRUPTION = "corruption"
    OTHER = "other"

class SentimentStatement(BaseModel):
    entity: str
    entity_type: EntityType
    issue: Optional[IssueType]
    polarity: int         # -1 negative, 0 neutral, 1 positive
    confidence: float     # 0.0 to 1.0
    location_mention: Optional[str]
    language: str

class ExtractionResult(BaseModel):
    statements: List[SentimentStatement]
    primary_language: str
    contains_bhojpuri: bool

EXTRACTION_PROMPT = """
You are a political sentiment extractor for Uttar Pradesh, India.

Input: Text in Hindi/Bhojpuri/English (already normalized to Hindi).
Output: JSON only. No prose, no explanation.

Task:
- Identify political entities: BJP (भाजपा), SP (समाजवादी पार्टी), BSP, Congress, or specific candidates.
- Identify issues from this fixed list: water, roads, electricity, jobs, women_safety, price_rise, farmer, sugarcane, health, education, corruption, other.
- Assign polarity: 1 (positive/praise), -1 (negative/criticism), 0 (neutral/factual).
- Extract any location mentions (village, ward, area, landmark names).
- If a comment has multiple statements, output one record per statement.

Text: {text}
"""
```

### 7.3 Political Lexicon (Seed List — expand with Person 13)

```python
PARTY_ALIASES = {
    "BJP": ["bjp", "भाजपा", "भारतीय जनता पार्टी", "कमल", "lotus", "sarkar", "modi sarkar",
            "yogi sarkar", "योगी सरकार", "मोदी सरकार", "double engine"],
    "SP": ["sp", "समाजवादी", "समाजवादी पार्टी", "cycle", "साइकिल", "akhilesh",
           "अखिलेश", "neta ji", "netaji", "mulayam"],
    "BSP": ["bsp", "बसपा", "बहुजन समाज पार्टी", "elephant", "हाथी", "mayawati", "behan ji"],
    "Congress": ["congress", "कांग्रेस", "INC", "rahul", "राहुल", "priyanka"],
}

ISSUE_TERMS = {
    "water": ["पानी", "water", "नल", "hand pump", "हैंडपंप", "पेयजल", "पीने का पानी"],
    "roads": ["सड़क", "road", "गड्ढे", "pothole", "पक्की सड़क"],
    "electricity": ["बिजली", "light", "load shedding", "लोड शेडिंग", "bijli"],
    "jobs": ["बेरोजगारी", "नौकरी", "रोजगार", "job", "unemployment", "rojgar"],
    "price_rise": ["महंगाई", "inflation", "price", "gas", "petrol", "dearness", "महंगा"],
    "farmer": ["किसान", "kisan", "farmer", "खेती", "crop", "fasal"],
    "sugarcane": ["गन्ना", "sugarcane", "ganna", "mill", "chini mill", "चीनी मिल"],
    "women_safety": ["महिला", "woman", "rape", "safety", "darinda", "सुरक्षा", "beti"],
}

SENTIMENT_POSITIVE_HI = ["अच्छा", "बढ़िया", "शानदार", "विकास", "तरक्की", "खुश", "धन्यवाद"]
SENTIMENT_NEGATIVE_HI = ["बुरा", "खराब", "बेकार", "भ्रष्टाचार", "धोखा", "झूठ", "नाराज"]
```

### 7.4 Geo-Entity Resolution

```python
from thefuzz import process
import pandas as pd

class GeoResolver:
    def __init__(self, booth_df, panchayat_df, village_df):
        # Build alias index: {name_string: (id, type, booth_ids)}
        self.alias_index = {}
        
        for _, row in booth_df.iterrows():
            names = [row["polling_station_name"], row["locality_hint"]]
            for name in names:
                if name:
                    self.alias_index[name.lower()] = {
                        "id": row["booth_id"], "type": "booth"
                    }
        
        for _, row in panchayat_df.iterrows():
            self.alias_index[row["gp_name"].lower()] = {
                "id": row["panchayat_id"], "type": "panchayat"
            }
        # Same for villages

    def resolve(self, location_text: str, threshold=80):
        if not location_text:
            return None, 0.0
        
        match, score = process.extractOne(
            location_text.lower(),
            list(self.alias_index.keys())
        )
        
        if score >= threshold:
            geo_confidence = score / 100.0
            return self.alias_index[match], geo_confidence
        return None, 0.0
```

---

## 8. Knowledge Graph Build Plan

### 8.1 Load Order (must respect dependencies)

```
Step 1: Load State, District nodes
Step 2: Load AssemblyConstituency nodes + HAS_DISTRICT, HAS_AC
Step 3: Load Booth nodes + HAS_BOOTH
Step 4: Load Party, Election nodes
Step 5: Load Candidate nodes + REPRESENTS, CONTESTS_IN, HAS_CANDIDATE_IN_ELECTION
Step 6: Load Panchayat, Village nodes + LOCATED_IN, HAS_VILLAGE
Step 7: Load Voter nodes (hashed) + HAS_VOTER
Step 8: Load VoterSegment nodes + BELONGS_TO_SEGMENT
Step 9: Load Scheme, SchemeBenefitEvent nodes + RECEIVED_BENEFIT, OF_SCHEME
Step 10: Load Issue nodes
Step 11: Load Grievance nodes + RAISED_GRIEVANCE, ABOUT_ISSUE
Step 12: Load PulseEvent nodes (from pulse_events table) + all relationships
Step 13: Run aggregation → HAS_AGGREGATE_SENTIMENT relationships
```

### 8.2 Neo4j Load Script Pattern

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def load_booths(booth_df):
    with driver.session() as session:
        # Use UNWIND for batch loading — much faster than one-by-one
        session.run("""
            UNWIND $rows AS row
            MERGE (b:Booth {booth_id: row.booth_id})
            SET b.booth_number = row.booth_number,
                b.polling_station_name = row.polling_station_name,
                b.address = row.address,
                b.total_voters = row.total_voters,
                b.male_voters = row.male_voters,
                b.female_voters = row.female_voters,
                b.lat = row.lat, b.lon = row.lon
            WITH b, row
            MATCH (a:AssemblyConstituency {ac_id: row.ac_id})
            MERGE (a)-[:HAS_BOOTH]->(b)
        """, rows=booth_df.to_dict("records"))

def load_pulse_events(events_df):
    with driver.session() as session:
        session.run("""
            UNWIND $rows AS row
            CREATE (pe:PulseEvent {
                event_id: row.id,
                source_type: row.source_type,
                polarity: row.final_polarity,
                confidence: row.confidence,
                issue: row.issue,
                entity: row.entity,
                created_at: datetime(row.created_at)
            })
            WITH pe, row
            MATCH (b:Booth {booth_id: row.mapped_booth_id})
            MERGE (pe)-[:MENTIONS_LOCATION]->(b)
            WITH pe, row
            MATCH (i:Issue {name: row.issue})
            MERGE (pe)-[:ABOUT_ISSUE]->(i)
        """, rows=events_df.to_dict("records"))
```

### 8.3 GraphRAG Layer (for analyst natural-language queries)

```python
from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI

graph = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASSWORD)

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True,
    allow_dangerous_requests=True
)

# Example analyst queries
chain.invoke("Which booths in Gorakhpur Urban have highest negative sentiment on BJP?")
chain.invoke("What are the top 3 issues in booths where women voters are majority?")
chain.invoke("Which panchayats have MGNREGA activities but high unemployment grievances?")
```

---

## 9. Analytics, Aggregation & Dashboard

### 9.1 Booth Metrics Aggregation Query

```sql
-- Run every 6 hours as Prefect flow
INSERT INTO booth_metrics (booth_id, window_start, window_end,
    bjp_pulse_score, opp_pulse_score, pain_index, top_issue,
    issue_breakdown, event_count, data_confidence)

SELECT
    mapped_booth_id AS booth_id,
    NOW() - INTERVAL '7 days' AS window_start,
    NOW() AS window_end,

    -- BJP sentiment score: avg polarity of BJP-targeted events
    AVG(CASE WHEN entity IN ('BJP','भाजपा') THEN polarity * confidence END)
        AS bjp_pulse_score,

    -- Opposition score
    AVG(CASE WHEN entity IN ('SP','BSP','Congress') THEN polarity * confidence END)
        AS opp_pulse_score,

    -- Pain index: proportion of negative events across all issues
    AVG(CASE WHEN polarity = -1 THEN confidence ELSE 0 END)
        AS pain_index,

    -- Top issue by event count
    MODE() WITHIN GROUP (ORDER BY issue) AS top_issue,

    -- Issue breakdown as JSON
    jsonb_object_agg(issue, ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER(), 3))
        AS issue_breakdown,

    COUNT(*) AS event_count,
    AVG(confidence * geo_confidence) AS data_confidence

FROM pulse_events
WHERE mapped_booth_id IS NOT NULL
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY mapped_booth_id;
```

### 9.2 Streamlit Dashboard Structure

```
Dashboard Pages:
├── Home: District overview map (Deck.gl) — booths colored by BJP pulse
├── AC Deep Dive: Select AC → booth list with metrics table
├── Booth Profile:
│   ├── Demographics (pie: male/female/age bands)
│   ├── Pulse chart (BJP vs Opp score over time)
│   ├── Issue radar chart
│   └── Recent PulseEvents (comments, news snippets)
├── Candidate Panel: Per-AC candidate comparison (affidavit data)
├── Segment Explorer: Filter segments by issue, age, scheme
└── Message Builder: Select segment → generate governance message
```

---

## 10. Messaging & Targeting Layer

### 10.1 Segment Query Examples (Cypher)

```cypher
// Segments with water issue and negative BJP sentiment in specific AC
MATCH (a:AssemblyConstituency {ac_id: "gorakhpur_urban"})
  -[:HAS_BOOTH]->(b:Booth)
  -[:HAS_VOTER]->(v:Voter)
  -[:BELONGS_TO_SEGMENT]->(s:VoterSegment)
WHERE s.top_issue = "water"
  AND EXISTS {
    MATCH (b)-[:HAS_AGGREGATE_SENTIMENT {issue:"water"}]->(i:Issue)
    WHERE i.polarity < 0
  }
RETURN s.segment_id, s.age_band, s.gender, s.approx_count, b.booth_id
ORDER BY s.approx_count DESC
```

### 10.2 Message Generation (Gemini)

```python
import google.generativeai as genai

def generate_governance_message(segment_profile: dict, booth_context: dict) -> str:
    prompt = f"""
You are writing a governance update message for a voter segment in Gorakhpur, UP.

Voter Segment Profile:
- Booth: {booth_context['polling_station_name']}
- Age Group: {segment_profile['age_band']}
- Gender: {segment_profile['gender']}
- Primary Issue: {segment_profile['top_issue']}

Recent Government Actions in this area:
{booth_context['recent_activities']}

Schemes available for this segment:
{booth_context['relevant_schemes']}

Write a SHORT governance update message (max 2 sentences) in Hindi.
Be specific to the local area. Do not mention party names.
Focus on government actions taken on the primary issue.
Output: Hindi message only, no English.
"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text

# Store in graph
def store_message(segment_id, message_text, channel="whatsapp"):
    with driver.session() as session:
        session.run("""
            MATCH (s:VoterSegment {segment_id: $seg_id})
            CREATE (m:Message {
                message_id: randomUUID(),
                text: $text, text_hi: $text,
                generated_at: datetime(),
                status: 'draft'
            })
            CREATE (ch:Channel {name: $channel})
            MERGE (s)-[:TARGETED_WITH {queued_at: datetime()}]->(m)
            MERGE (m)-[:VIA]->(ch)
        """, seg_id=segment_id, text=message_text, channel=channel)
```

### 10.3 Delivery Integration (Gupshup / Karix)

```python
import requests

def send_whatsapp_message(phone_number: str, message: str, template_name: str):
    # Gupshup WhatsApp Business API
    # NOTE: Phone numbers come from SECURE external system — not Neo4j
    url = "https://api.gupshup.io/sm/api/v1/msg"
    payload = {
        "channel": "whatsapp",
        "source": "YOUR_WABA_NUMBER",
        "destination": phone_number,
        "message": json.dumps({"type": "text", "text": message}),
        "src.name": "YourAppName"
    }
    headers = {"apikey": GUPSHUP_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=payload, headers=headers)
    return resp.json()
```

---

## 11. Security & Compliance

### 11.1 PII Architecture

```
SECURE ZONE (never exposed to Neo4j or dashboard):
┌──────────────────────────────────────────────┐
│  pii_vault table (PostgreSQL, restricted access)│
│  voter_uid (hash) | epic_number | phone | name│
└──────────────────────────────────────────────┘

GRAPH / ANALYTICS ZONE (no PII):
┌──────────────────────────────────────────────┐
│  Voter node: voter_uid | age_band | gender   │
│  No name, no EPIC, no phone                  │
└──────────────────────────────────────────────┘

Hashing: voter_uid = SHA256(epic_number + booth_id + salt)
Salt: stored in environment variable, never in code
```

### 11.2 Legal Checklist

- [ ] Legal review of electoral roll usage (RPA 1951 compliance)
- [ ] DLT registration for bulk SMS (mandatory in India under TRAI)
- [ ] WhatsApp Business API — only send to opted-in numbers
- [ ] Data retention policy — how long to keep raw comments?
- [ ] Access control — who can query voter-level data?
- [ ] Audit log for all PII accesses

### 11.3 RBAC (Role-Based Access Control)

```
Roles:
  ANALYST     → Read dashboard, run pre-built queries, view booth metrics
  DATA_ENG    → Read/write raw tables, run ETL pipelines
  GRAPH_ENG   → Read/write Neo4j, run Cypher queries
  ADMIN       → All permissions + PII access + user management
  FIELD_AGENT → Submit surveys via KoBoToolbox only
```

---

## 12. 15-Person Work Distribution — Step by Step

### Quick Reference Map

| Person | Title | Layer | Priority |
|---|---|---|---|
| P1 | Tech Lead / Architect | All | P0 |
| P2 | DevOps & Infra | L0 | P0 |
| P3 | Data Engineer – Official Sources | L1, L2 | P0 |
| P4 | Data Engineer – Dynamic Signals | L1, L2 | P1 |
| P5 | Data Engineer – ETL & Pipelines | L2 | P0 |
| P6 | NLP Engineer – Language & Translation | L3 | P1 |
| P7 | NLP/ML Engineer – Sentiment Extraction | L3 | P1 |
| P8 | NLP Engineer – Entity Resolution | L3 | P1 |
| P9 | Graph Engineer | L4 | P0 |
| P10 | Backend Engineer | L6 | P2 |
| P11 | Analytics Engineer | L5 | P2 |
| P12 | Frontend / Dashboard Engineer | L7 | P2 |
| P13 | Domain Specialist – UP Politics | L1, L3, L4 | P0 |
| P14 | Field Operations & Data Coordinator | L1, L7 | P1 |
| P15 | Security & Compliance Lead | L0 | P0 |

---

### P1 — Tech Lead / Architect

**Goal:** Own the overall system design, unblock everyone, ensure all pieces integrate correctly.

**Week 1 (Days 1–5):**
1. Day 1: Write the project `README.md` and set up the Git monorepo structure (`/data`, `/flows`, `/nlp`, `/graph`, `/api`, `/dashboard`, `/docs`).
2. Day 1: Lock the Neo4j schema with P9 — finalize all node labels, relationship types, property names. Write it as `docs/graph-schema.md`.
3. Day 1: Define all environment variables and create `.env.example` for the team.
4. Day 2: Conduct kick-off call with all 15 — assign tasks, share this document.
5. Day 2: Review P15's PII architecture before P3 starts electoral roll work.
6. Day 3: Review P3's first scraper output — validate that `booth_master` schema matches graph load expectations.
7. Day 4: Integrate first end-to-end test: P3 data → P5 ETL → P9 Neo4j load → P12 dashboard displays a booth.
8. Day 5: Resolve blockers. Prioritize what's on critical path.

**Week 2 (Days 6–10):**
1. Day 6: Review NLP pipeline output (P7) — validate 100 sample pulse events manually.
2. Day 7: Code review for Neo4j loaders (P9) and FastAPI endpoints (P10).
3. Day 8: Integration test: full pipeline from YouTube comment → pulse_event → Neo4j → dashboard booth pulse chart.
4. Day 9: Review aggregation query output (P11) — verify booth_metrics math is correct.
5. Day 10: Team demo. Identify what's broken. Prioritize fixes vs. new features for Week 3.

**Week 3–5:**
1. Oversee scaling from 1 AC to 2 ACs.
2. Introduce GraphRAG layer with P9 and P10.
3. Architecture review of messaging delivery (P10 + P14).
4. Performance tuning: identify slow Neo4j queries, add indexes.

---

### P2 — DevOps & Infrastructure Engineer

**Goal:** Get all shared infrastructure running so the team has somewhere to develop and deploy.

**Day 1:**
1. Create shared cloud accounts (or configure on-prem server):
   - Neon.tech account → create `gorakhpur_db` PostgreSQL database
   - AuraDB free tier → create Neo4j instance, save URI + credentials
   - Upstash → create Redis instance
   - Prefect Cloud → create workspace, invite all team members
2. Create GitHub repository, set up branch protection on `main`
3. Set up shared `.env` file in password manager (1Password / Bitwarden) — **never in Git**
4. Share all credentials with P1 and P15 only

**Day 2:**
1. Write `docker-compose.yml` for local development (PostgreSQL + Neo4j + Redis + Prefect server)
2. Run `docker-compose up` and verify all services start
3. Run SQL DDL scripts to create all tables in `gorakhpur_db`
4. Run Neo4j constraints and index Cypher (from Section 3.6)
5. Verify P3 can connect to PostgreSQL from their machine

**Day 3:**
1. Set up Prefect deployment: `prefect server start` or configure Prefect Cloud connection
2. Create a test flow that runs `SELECT 1` from PostgreSQL and `MATCH (n) RETURN count(n)` from Neo4j — confirms connectivity
3. Set up GitHub Actions CI: on every PR, run `pytest tests/unit/`
4. Set up MinIO (or S3) for raw PDF/video storage

**Day 4–5:**
1. Set up Grafana + Prometheus for pipeline monitoring (optional but important for Week 2+)
2. Write deployment guide (`docs/setup.md`) so any team member can reproduce the environment
3. Help P3 and P4 debug any connectivity issues

**Week 2–5:**
1. Monitor Prefect flow run failures — alert the relevant engineer
2. Add database backups (pg_dump daily to S3)
3. Scale infrastructure if needed (Neo4j upgrade, PostgreSQL connection pooling with PgBouncer)
4. Set up staging vs. production environments when project stabilizes

---

### P3 — Data Engineer — Official Sources

**Goal:** Get all official structured data (ECI booths, candidates, electoral rolls, historical results) into PostgreSQL, clean and validated.

**Day 1:**
1. Verify legal clearance from P15 before starting electoral roll work
2. Manually explore `https://ceouttarpradesh.nic.in/` and map all pages needed
3. Write `scrapers/eci_booths.py`:
   - Scrape AC list for Gorakhpur district
   - Scrape booth list for Gorakhpur Urban AC
   - Parse booth name, address, BLO contact
   - Load into `ac_master` and `booth_master`
4. Run scraper, verify ~300 rows in `booth_master` for Gorakhpur Urban

**Day 2:**
1. Write `scrapers/myneta_candidates.py`:
   - Scrape Gorakhpur Urban candidates from MyNeta
   - Extract name, party, criminal cases, assets, liabilities
   - Download affidavit PDFs to S3/MinIO
   - Load into `candidate_master` and `candidate_affidavits`
2. Write `scrapers/eci_results.py`:
   - Scrape 2022 Assembly results for Gorakhpur Urban
   - Load into `election_results`

**Day 3:**
1. Write `scrapers/electoral_rolls.py` (after legal clearance from P15):
   - Download electoral roll PDFs for Gorakhpur Urban booths
   - Use `pdfplumber` to parse: parse voter counts per booth
   - If PDF is scanned/image: use `pytesseract` OCR
   - Load aggregated counts (NOT individual rows) into `electoral_roll_summary`
   - Hashed voter IDs only into `electoral_roll_hashed` table
2. Add retry decorator to all scrapers (government sites go down frequently)

**Day 4:**
1. Write `scrapers/egramswaraj.py`:
   - Scrape panchayat list for Gorakhpur district
   - Get development activities per panchayat for pilot ACs
   - Load into `panchayat_master` and `panchayat_activity`
2. Manual validation: spot-check 10 booths — do the names/addresses look right?

**Day 5:**
1. Write Prefect flows for each scraper (so they can be scheduled)
2. Write `tests/test_scrapers.py` — check row counts, no nulls in key columns, valid IDs
3. Hand off `booth_master` and `candidate_master` to P9 for graph loading

**Week 2+:**
1. Add Campierganj AC data
2. Scrape MGNREGA and PMAY beneficiary data (SOURCE-06, 07)
3. Scrape Jansunwai grievances (SOURCE-08)
4. Keep scrapers maintained as government websites update

---

### P4 — Data Engineer — Dynamic Signals

**Goal:** Build and maintain ingestion pipelines for YouTube comments, local news, and social media.

**Day 1:**
1. Identify 20–30 YouTube channels/videos to target:
   - Search: "गोरखपुर चुनाव", "gorakhpur BJP SP", "UP Tak gorakhpur", "Yogi gorakhpur"
   - Build initial list in `data/yt_channel_seeds.csv`: channel_id, channel_name, relevance_score
2. Write `scrapers/youtube_comments.py`:
   - Use `yt-dlp` to fetch comments without API key for initial batch
   - Store in `yt_videos` and `yt_comments` tables

**Day 2:**
1. Set up YouTube Data API v3 key (free, 10k units/day)
2. Upgrade scraper to use API for structured, paginated comment collection
3. Write `scrapers/youtube_search.py` — periodic search for new Gorakhpur political videos
4. Test: collect 5,000+ comments, verify Hindi/Bhojpuri text is stored correctly (UTF-8)

**Day 3:**
1. Write `scrapers/news_jagran.py`:
   - Scrape Jagran Gorakhpur section, last 7 days of articles
   - Extract: headline, body, date, URL
   - Use `newspaper3k` for body extraction
2. Write `scrapers/news_amarujala.py` (same pattern)
3. Load all articles into `news_articles` table

**Day 4:**
1. Write `scrapers/news_generic.py` using `feedparser` (RSS feeds) for other portals
2. Add deduplication: hash URL to prevent re-ingesting same article
3. Test: 200+ unique articles collected

**Day 5:**
1. Wrap all scrapers as Prefect tasks in `flows/dynamic_signals/flow_youtube.py` and `flow_news.py`
2. Schedule: `cron="0 */6 * * *"` (every 6 hours)
3. Add alerting: if 0 new comments collected in a run, send Prefect alert

**Week 2+:**
1. Add X/Twitter API integration (if API key obtained)
2. Build deduplication for comments (same user, same text on multiple videos)
3. Track video engagement metrics (views, likes) as context for sentiment weighting

---

### P5 — Data Engineer — ETL & Pipelines

**Goal:** Build the transformation layer that cleans, validates, joins, and prepares all data for the NLP pipeline and graph.

**Day 1:**
1. Set up `great_expectations` for data quality checks on `booth_master` (when P3 delivers):
   - booth_id must be unique and non-null
   - total_voters must be between 100 and 2000 (reasonable range)
   - lat/lon must be within Gorakhpur bounds
2. Write `etl/booth_panchayat_join.py`:
   - Fuzzy match booth locality_hint against panchayat_master.gp_name
   - Use `thefuzz` — score > 80 = confirmed match; 60–80 = manual review queue
   - Output: `booth_panchayat_mapping` table

**Day 2:**
1. Write `etl/voter_segment_builder.py`:
   - From `electoral_roll_summary`, create VoterSegment records:
     - (booth_id, "young_men", 18-25, Male, approx_count)
     - (booth_id, "young_women", 18-25, Female, approx_count)
     - etc.
   - Load into `voter_segments` table
2. Write `etl/voter_hasher.py` (with P15 review):
   - If raw electoral roll data available: hash EPIC + booth_id + SALT → voter_uid
   - Load hashed rows into `electoral_roll_hashed`

**Day 3:**
1. Write `etl/pulse_event_prep.py`:
   - Read from `yt_comments` and `news_articles`
   - Deduplicate by content hash
   - Add `source_type`, `source_id` columns
   - Write to `pulse_events_raw` (pre-NLP staging table)
2. Test: 10,000+ rows in `pulse_events_raw`

**Day 4:**
1. Write `etl/data_quality_report.py`:
   - Daily report: row counts per table, null rates, scraper freshness
   - Send to Prefect/Slack notification
2. Write Alembic migrations for any schema changes

**Day 5:**
1. Wrap all ETL as Prefect flows
2. Write integration test: run full data flow from raw tables → staging tables → verify counts
3. Coordinate with P6 and P7 on input format they need for NLP pipeline

**Week 2+:**
1. Add field survey data ETL (from KoBoToolbox, when P14 delivers forms)
2. Add schema for booth agent reports
3. Performance tuning: add indexes on `pulse_events_raw`, batch processing for large datasets

---

### P6 — NLP Engineer — Language Detection & Translation

**Goal:** Build Stage 1–3 of the NLP pipeline: language detection, text cleaning, Bhashini normalization.

**Day 1:**
1. Set up Bhashini API account at `https://bhashini.gov.in/ulca/auth/register`
2. Get API key and test translation endpoint:
   ```python
   # Test: Bhojpuri → Hindi translation
   POST https://dhruva-api.bhashini.gov.in/services/inference/pipeline
   ```
3. Write `nlp/language_detector.py` using `langdetect` + `fastText` LID model
4. Test on 100 sample comments: what % are Hindi, Bhojpuri, English, mixed?

**Day 2:**
1. Write `nlp/text_cleaner.py`:
   - Remove URLs (`https://...`)
   - Normalize Unicode (NFC normalization)
   - Remove repeated characters ("aachhaaa" → "achha")
   - Handle Roman-script Hindi (convert using IndicTrans2 or `indic-transliteration` library)
2. Test on 500 sample comments

**Day 3:**
1. Write `nlp/bhashini_translator.py`:
   - POST to Bhashini API with Bhojpuri/mixed text
   - Handle rate limits (add exponential backoff)
   - Store `normalized_hi` in staging table
2. Write fallback: if Bhashini fails, use `IndicTrans2` local model (slower but offline)
3. Test: 200 Bhojpuri comments translated — manual review with P13 for quality

**Day 4:**
1. Benchmark Bhashini API: latency, rate limits, quality for political text
2. Document known failure cases (very dialectal phrases, political slang)
3. Build a test suite of 50 manually verified translations for regression testing

**Day 5:**
1. Integrate with P5's `pulse_events_raw` table: read → clean → translate → write `text_normalized_hi`
2. Wrap as Prefect task: `normalize_text_task`
3. Coordinate with P7 on input format for LLM extraction

**Week 2+:**
1. Expand test suite to 200 samples with P13
2. Add support for English-Hindi code-mixing (common in urban Gorakhpur)
3. Build dialect-specific word lists with P13 (Bhojpuri terms not in Bhashini dictionary)

---

### P7 — NLP/ML Engineer — Sentiment Extraction

**Goal:** Build Stage 4 of NLP pipeline — LLM extraction + rule-based fallback + quality scoring.

**Day 1:**
1. Set up Groq API account (free tier: generous LPM limits) and test `llama3-70b-8192`
2. Write `nlp/sentiment_extractor.py`:
   - Build the `ExtractionResult` Pydantic schema (from Section 7.2)
   - Set up `instructor` library with Groq client
   - Write the extraction prompt (from Section 7.2)
3. Test on 10 sample Hindi political texts — verify JSON output structure

**Day 2:**
1. Write `nlp/lexicon_classifier.py` (rule-based fallback):
   - Load political lexicon from P13 (or use seed from Section 7.3)
   - Keyword matching for party, issue, sentiment
   - Output same schema as LLM extractor
2. Write fallback logic: if LLM confidence < 0.6 → use rule output

**Day 3:**
1. Run extraction on 1,000 comments from `pulse_events_raw`
2. Evaluate: how many extracted successfully? Average confidence? Common failures?
3. Iterate on prompt: add few-shot examples for common failure cases
4. Track: LLM cost per 1000 texts (Groq is very cheap, but track anyway)

**Day 4:**
1. Write QA comparison: for each text, store both LLM and rule outputs in `llm_output` and `rule_output` JSONB columns
2. Write `nlp/final_policy.py`: deterministic rules for when to use LLM vs rule output
3. Store `final_polarity` in `pulse_events` table

**Day 5:**
1. Wrap full extraction pipeline as Prefect flow: `flows/nlp/flow_sentiment_extract.py`
2. Write `tests/test_sentiment.py` with 50 labeled examples (labeled by P13)
3. Coordinate with P8: pass `location_mention` field for geo resolution

**Week 2+:**
1. Expand prompt with few-shot examples for Bhojpuri-specific idioms
2. Set up `Promptfoo` for A/B testing different prompt versions
3. Start labeling dataset for fine-tuning IndicBERT (long-term cost reduction)
4. Add caste/community entity extraction

---

### P8 — NLP Engineer — Entity Resolution & NER

**Goal:** Build Stage 5–6 of NLP pipeline: caste NER and geo-entity resolution (text location → booth ID).

**Day 1:**
1. Build the geo-resolution alias index from `booth_master`, `panchayat_master`, `village_master` (when P3 delivers)
2. Write `nlp/geo_resolver.py` using `thefuzz` (Section 7.4)
3. Test on 50 manually created test cases: "Deoria Naka" → booth_id, geo_confidence

**Day 2:**
1. Improve resolution with `sentence-transformers`:
   - Encode all place names with `paraphrase-multilingual-MiniLM-L12-v2`
   - Store embeddings in PostgreSQL using `pgvector`
   - Semantic similarity fallback when fuzzy score < 80
2. Test: does embedding-based matching find "Deoria Naka" from "Deoria Naaka" or "देवरिया नाका"?

**Day 3:**
1. Write `nlp/community_ner.py`:
   - Build regex + keyword patterns for caste/community mentions:
     - Yadav, यादव, OBC, Dalit, दलित, Brahmin, ब्राह्मण, Muslim, Kurmi, etc.
   - Tag extracted community mentions in pulse_events
   - Add `community_tags: List[str]` field to `ExtractionResult`
2. Review patterns with P13 for accuracy on UP political context

**Day 4:**
1. Integrate geo resolver into the Prefect NLP flow (after P7's extraction step)
2. Write quality metrics: what % of pulse events get a high-confidence booth mapping?
3. Build manual review queue: events with `geo_confidence` between 0.5–0.8

**Day 5:**
1. Write location alias supplement file: manually add common Gorakhpur area names, landmarks, wards that don't appear in official data
2. Coordinate with P14 to get field agent knowledge of local place names

**Week 2+:**
1. Train custom NER model for Gorakhpur-specific location recognition
2. Add booth agent reports as another source of location aliases
3. Build deduplication: if same event (same text, different source) → merge, don't double-count

---

### P9 — Graph Engineer

**Goal:** Build and maintain the Neo4j knowledge graph — schema, loaders, Cypher query library, and GraphRAG layer.

**Day 1:**
1. Lock graph schema with P1 — write `docs/graph-schema.md` (node labels, relationship types, properties)
2. Run constraints and indexes (Section 3.6) on Neo4j instance
3. Write `graph/loaders/load_structure.py`:
   - Load `State`, `District`, `AssemblyConstituency` nodes
   - Use MERGE (not CREATE) to be idempotent
4. Test: query `MATCH (a:AssemblyConstituency) RETURN a.name` — confirm Gorakhpur Urban appears

**Day 2:**
1. Write `graph/loaders/load_booths.py`:
   - Batch UNWIND load of all booths from `booth_master`
   - Create `HAS_BOOTH` relationships
2. Write `graph/loaders/load_candidates.py`:
   - Load `Candidate`, `Party`, `Election` nodes
   - Create `REPRESENTS`, `CONTESTS_IN`, `HAS_CANDIDATE_IN_ELECTION`
3. Write `graph/loaders/load_panchayats.py`:
   - Load `Panchayat`, `Village`, `Activity`, `Scheme` nodes
   - Create `LOCATED_IN`, `HAS_ACTIVITY`, `OF_SCHEME`

**Day 3:**
1. Write `graph/loaders/load_voters.py`:
   - From `electoral_roll_hashed`: load hashed `Voter` nodes with age_band, gender
   - Create `HAS_VOTER` relationships
   - Create `VoterSegment` nodes from `voter_segments` table
   - Create `BELONGS_TO_SEGMENT` relationships
2. Write `graph/loaders/load_pulse_events.py`:
   - Incremental load: only pulse_events with `created_at > last_loaded_at`
   - Create `PulseEvent` nodes + `ABOUT_ISSUE`, `TARGETS`, `MENTIONS_LOCATION`

**Day 4:**
1. Write `graph/queries/cypher_library.py`:
   - `get_booth_pulse_score(booth_id, window_days)` — returns BJP vs opp score
   - `get_booth_top_issues(booth_id)` — returns ranked issue list
   - `get_segments_by_issue(ac_id, issue)` — returns VoterSegments
   - `get_candidate_profile(candidate_id)` — returns full candidate node
2. Test each query, verify output format matches dashboard expectations

**Day 5:**
1. Set up GraphRAG layer (Section 8.3):
   - Configure LangChain `GraphCypherQAChain` with Neo4j
   - Test 5 natural language queries — does Cypher generated look correct?
2. Coordinate with P10 on FastAPI endpoint for GraphRAG queries
3. Write `tests/test_graph_loaders.py` — verify node/relationship counts after load

**Week 2+:**
1. Add aggregation relationships: `HAS_AGGREGATE_SENTIMENT` computed by P11
2. Optimize slow Cypher queries with EXPLAIN / PROFILE
3. Add vector index on `PulseEvent.text_normalized_hi` for semantic search
4. Implement BoothAgent nodes when P14 delivers agent reports

---

### P10 — Backend Engineer

**Goal:** Build the FastAPI layer that exposes graph and analytics data to the dashboard and external systems.

**Day 1–2 (parallel with P9 — can start with mock data):**
1. Set up FastAPI project structure:
   ```
   api/
     main.py
     routers/
       booths.py, candidates.py, segments.py, messages.py, query.py
     models/
       schemas.py  (Pydantic response models)
     db/
       neo4j_client.py, postgres_client.py, redis_client.py
   ```
2. Write health check endpoint: `GET /health` → checks DB connectivity

**Day 3:**
1. Write `GET /booth/{booth_id}` — returns booth details + latest metrics
2. Write `GET /ac/{ac_id}/booths` — returns all booths for an AC with metrics
3. Write `GET /ac/{ac_id}/candidates` — returns candidate list with affidavit data
4. Add Redis caching: booth metrics cached for 1 hour (avoids Neo4j hammering)

**Day 4:**
1. Write `GET /booth/{booth_id}/pulse` — time-series pulse scores
2. Write `GET /segment/{segment_id}` — segment profile
3. Write `POST /query` — natural language query via GraphRAG (calls P9's LangChain setup)
4. Write `POST /message/generate` — takes segment_id, calls Gemini, returns draft message

**Day 5:**
1. Add JWT authentication (or API key auth for MVP)
2. Write OpenAPI documentation — `GET /docs` should show all endpoints clearly
3. Deploy to Railway.app or Render (free tier) — share URL with P12

**Week 2+:**
1. Add `POST /message/send` — queues messages for WhatsApp delivery
2. Add `GET /alerts` — returns booths where pulse changed > 20% in 24h
3. Add `GET /booth/{booth_id}/pulse` time-series chart data endpoint

---

### P11 — Analytics Engineer

**Goal:** Build aggregation jobs that compute booth-level metrics, caste-issue cross-tabs, and trend analysis.

**Day 1–2 (after P3 delivers booth data and P7 delivers pulse events):**
1. Write SQL aggregation function for `booth_metrics` (Section 9.1)
2. Test on sample data — verify BJP pulse score makes intuitive sense for known booths

**Day 3:**
1. Write caste-issue cross-tab aggregation:
   - Group PulseEvents by community tag + issue + polarity
   - Result: "Yadav voters most negative on sugarcane price, not roads"
   - Load into `caste_issue_metrics` table
2. Write trend detection query:
   - Compare this week's booth pulse to last week's
   - Flag booths where `|delta_score| > 0.2` as "movement detected"

**Day 4:**
1. Write VoterSegment scoring update:
   - Compute `issue_salience_score` per segment from linked PulseEvents
   - Update `VoterSegment` node properties in Neo4j (via P9's loader pattern)
2. Write data confidence score per booth:
   - Based on: event count, source diversity, avg geo_confidence
   - Low confidence booths should be flagged in dashboard

**Day 5:**
1. Wrap all aggregations as Prefect flows: `flows/aggregation/flow_booth_metrics.py`
2. Schedule every 6 hours
3. Add PostGIS spatial cluster analysis:
   - Which booths cluster geographically with similar pulse profiles?
   - Output: `booth_spatial_clusters` table for map visualization

**Week 2+:**
1. Add historical comparison: current election cycle vs. 2022 results
2. Build "swing booth" analysis — booths with BJP/Opp pulse gap < 0.1
3. Add scheme delivery efficiency score: schemes delivered vs. grievances raised

---

### P12 — Frontend / Dashboard Engineer

**Goal:** Build the Streamlit analyst console and later a map-based visualization.

**Day 1–2 (can start with mock data from P10's API):**
1. Set up Streamlit project: `dashboard/app.py`
2. Build sidebar: District → AC → Booth selection dropdowns
3. Build `Home` page: AC-level summary table (booths count, avg pulse, top issue)

**Day 3:**
1. Build `Booth Profile` page:
   - Demographics: pie chart (male/female, age bands) using Plotly
   - Pulse chart: BJP vs Opposition score over time (line chart)
   - Issue radar chart: 8 issues with their sentiment scores
2. Build `Candidate Panel` page:
   - Per-AC candidate table: name, party, criminal cases, assets
   - Sortable by any column

**Day 4:**
1. Build `Pulse Events Feed`:
   - Table of recent comments/news that drove sentiment
   - Color-coded by polarity (red = negative, green = positive)
2. Build `Segment Explorer` page:
   - Filter: age band, gender, issue, AC
   - Display matching VoterSegments with counts

**Day 5:**
1. Build Folium/Pydeck map for geo visualization:
   - Choropleth: booths colored by BJP pulse score
   - Click a booth → show popup with pulse summary
2. Deploy to Streamlit Community Cloud (free) — share URL with full team

**Week 2+:**
1. Add `Message Builder` page:
   - Select segment → Generate message (calls P10's `/message/generate`)
   - Edit + approve message
   - Queue for delivery
2. Add `Alerts` panel: booths with sudden pulse shifts
3. Migrate to Next.js/React for better performance (if stakeholder demos require it)

---

### P13 — Domain Specialist — UP Politics

**Goal:** Provide UP politics domain knowledge — build the political lexicon, validate ontology entities, review NLP output quality.

**Day 1 (most critical day for this role):**
1. Write `data/lexicons/party_aliases.json` (comprehensive version of Section 7.3):
   - Every known alias for BJP, SP, BSP, Congress, allies in Hindi/Bhojpuri/English
   - Include local names (e.g., "Yogi sarkar", "double engine", "uncle ji" for SP)
2. Write `data/lexicons/issue_terms.json`:
   - Issue terms in Hindi + Bhojpuri + local Gorakhpur usage
   - Add Gorakhpur-specific issues: sugarcane mills (ganna), the CM being from Gorakhpur, temple issues
3. Write `data/lexicons/caste_community.json`:
   - All caste/community names relevant to Gorakhpur in Hindi/Bhojpuri
   - Which issues are particularly salient for which communities (background knowledge)

**Day 2:**
1. Review Neo4j schema (P9's draft) — are all relevant political entities modeled?
   - Suggest: add `LocalInfluencer` node (religious leaders, local celebrities who endorse candidates)
   - Suggest: add community dimension to `VoterSegment`
2. Write `data/gorakhpur_geography.md`:
   - List of all wards in Gorakhpur Urban AC with common names
   - List of major localities, mohallas, landmarks
   - Common alternate spellings of place names
   - This directly helps P8's geo-resolution

**Day 3:**
1. Label 200 sample comments (from P4's YouTube data) with:
   - `entity`, `entity_type`, `issue`, `polarity`
   - This becomes the NLP evaluation dataset
2. Provide to P7 as `data/labeled/sentiment_eval_200.jsonl`

**Day 4:**
1. Review 50 NLP pipeline outputs (from P7's first run) — validate against ground truth
2. Identify systematic errors: common misclassifications, missing entity aliases
3. Update lexicons based on errors found — share updated files with P7

**Day 5:**
1. Write a `data/gorakhpur_political_context.md`:
   - Current political landscape of Gorakhpur Urban
   - Key local issues as of latest information
   - Key candidates and their community support bases
   - This is used as context in LLM prompts

**Week 2+:**
1. Weekly review of 50 new NLP outputs — ongoing quality assurance
2. Map booth agent network: which panchayats/wards have reliable data vs. blind spots
3. Validate aggregated booth metrics against your own political intuition — flag anomalies
4. Expand to Campierganj AC — write equivalent lexicon supplements

---

### P14 — Field Operations & Data Coordinator

**Goal:** Design and run the field data collection system — surveys, booth agent network, IVR.

**Day 1:**
1. Set up KoBoToolbox account at `https://www.kobotoolbox.org/` (free for NGO/research)
2. Design Survey Form v1 with these questions:
   - Booth ID (dropdown from booth_master — auto-populated by field agent)
   - Top issues facing area (multi-select: water, roads, electricity, jobs, etc.)
   - Candidate preference (BJP / SP / BSP / Other / Undecided)
   - Scheme awareness: Did you or family receive [MGNREGA/PMAY/Ujjwala]? Yes/No
   - Satisfaction with government: 1–5 scale
   - Age band + Gender (not name)
3. Share form link with P1 for review

**Day 2:**
1. Write field agent onboarding guide (`docs/field-agent-guide.md`):
   - How to use KoBoToolbox on mobile (works offline)
   - How to select correct booth ID
   - Survey ethics: explain purpose, no name collection, voluntary
2. Set up 5 test respondents — run through survey end-to-end, fix UX issues

**Day 3:**
1. Coordinate with P5 on ETL for KoBoToolbox submissions:
   - KoBoToolbox exports to CSV or has REST API
   - Map form field names → `survey_responses` table columns
2. Write booth agent report form (simpler, 5 questions):
   - WhatsApp Business form or Google Form for daily/weekly booth agent updates
   - Booth ID, mood assessment (1–5), key issue mentioned today, turnout estimate

**Day 4:**
1. Start coordinating with actual field agents (if available):
   - Brief them on the survey
   - Assign booth coverage (which agent covers which booths)
   - Set up a WhatsApp group for field coordination
2. Run pilot: 2–3 field agents complete surveys for 10 booths

**Day 5:**
1. Review first batch of field submissions:
   - Are booth IDs being selected correctly?
   - Are all required fields filled?
   - Any questions causing confusion?
2. Iterate on form design based on feedback
3. Report to P1 and P11: field data quality assessment

**Week 2+:**
1. Scale to 20+ field agents, full coverage of pilot AC
2. Set up IVR survey with Exotel (trial account available)
3. Track field coverage: which booths have survey data vs. digital-only data
4. Build ground-truth comparison: field sentiment vs. NLP-computed sentiment for same booths

---

### P15 — Security & Compliance Lead

**Goal:** Ensure PII is handled legally and safely, compliance with Indian data laws, and access control.

**Day 1 (critical — must be done before P3 starts electoral roll work):**
1. Review RPA 1951 restrictions on electoral roll usage:
   - Electoral rolls ARE public, but prohibited uses include: commercial purpose, canvassing for votes in ways not authorized
   - Write `docs/legal-compliance.md` with: permitted uses, prohibited uses, our project's use case
   - Get sign-off from project owner on legal position
2. Define PII architecture (Section 11.1):
   - SHA-256 hash function for voter_uid: `hash = SHA256(epic_number + booth_id + SALT)`
   - Salt = random 32-byte string, stored in P2's environment config only
   - `pii_vault` table: restricted PostgreSQL schema, separate credentials
3. Write and share with P3: exactly which data they can and cannot store

**Day 2:**
1. Set up RBAC on PostgreSQL:
   - Create roles: `analyst_role`, `data_eng_role`, `graph_eng_role`, `admin_role`
   - Grant minimal permissions per role
   - `pii_vault` schema: accessible only to `admin_role`
2. Set up Neo4j access control (if using Enterprise) or document manual access control policy

**Day 3:**
1. Initiate DLT registration for bulk SMS (if messaging layer is in scope):
   - Register on any telecom provider's DLT platform (Jio, Airtel, Vi)
   - Required before any bulk SMS/WhatsApp outreach
2. Write consent management spec for messaging:
   - Only send to opted-in numbers
   - Every message must include opt-out instructions
   - Track consent status in `pii_vault`

**Day 4:**
1. Write data retention policy:
   - Raw YouTube comments: retain 90 days
   - `pulse_events`: retain indefinitely (anonymised)
   - Electoral roll raw: delete after creating `electoral_roll_summary`
   - Affidavit PDFs: retain indefinitely (public document)
2. Implement audit log trigger on `pii_vault` table:
   ```sql
   CREATE TABLE pii_access_log (
     user_name TEXT, action TEXT, accessed_at TIMESTAMPTZ, row_count INT
   );
   -- Add trigger to log every SELECT/UPDATE on pii_vault
   ```

**Day 5:**
1. Security review of P7's LLM prompts:
   - Are any voter details being sent to Groq/Gemini? (They must not be)
   - Verify: only normalized text (no names, IDs) goes to external APIs
2. Write security checklist in `docs/security-checklist.md`
3. Review P2's infrastructure setup — are credentials in env vars (not hardcoded)?

**Week 2+:**
1. Quarterly access review: who has what permissions?
2. Monitor `pii_access_log` for unusual access patterns
3. As messaging layer activates: audit all outgoing messages for compliance

---

## 13. Project Timeline

### 5-Week Overview

```
Week 1: Backbone — Infrastructure, Official Data, Graph Schema
Week 2: NLP Pipeline — Sentiment on 10,000+ texts
Week 3: Dashboard v1 — Booth pulse visible, candidates shown
Week 4: Field Data + Aggregation — Ground truth + metrics
Week 5: Messaging Layer + Scaling to 2nd AC
```

### Gantt View (by person/task)

```
         Day: 1  2  3  4  5  6  7  8  9  10 11 12 13 14 ...
P2 Infra:    [██████]
P15 Legal:   [████]
P1 Schema:   [████]
P3 Scrapers: [░░][████████████]
P9 Graph:    [░░][████████████]
P13 Lexicon: [████████████]
P4 YouTube:  [░░][████████████]
P5 ETL:      [░░][████████████]
P6 Language: [░░░░][████████]
P7 Sentiment:[░░░░░░][████████]
P8 GeoNER:   [░░░░][████████]
P10 API:     [░░░░░░][████████]
P11 Metrics: [░░░░░░░░][████]
P12 Dashboard[░░░░░░░░][████]
P14 Field:   [░░][████████████████]

[████] = active work   [░░░░] = waiting for dependency
```

### Milestones

| Milestone | Target Day | Owned by | Depends on |
|---|---|---|---|
| M1: DB + Neo4j running | Day 2 | P2 | — |
| M2: PII policy locked | Day 2 | P15 | — |
| M3: booth_master populated | Day 3 | P3 | M1 |
| M4: Neo4j geo-hierarchy loaded | Day 4 | P9 | M3 |
| M5: Lexicon v1 complete | Day 3 | P13 | — |
| M6: 10k YouTube comments collected | Day 4 | P4 | M1 |
| M7: NLP pipeline end-to-end working | Day 8 | P6,P7,P8 | M5, M6 |
| M8: pulse_events loading into Neo4j | Day 9 | P9 | M7, M4 |
| M9: booth_metrics aggregation running | Day 10 | P11 | M8 |
| M10: Dashboard v1 showing pulse | Day 12 | P12, P10 | M9 |
| M11: Field surveys running | Day 10 | P14 | M3 |
| M12: Messaging layer live | Day 25+ | P10, P14 | M10, M11 |
| M13: Campierganj AC added | Day 28+ | P3, P9 | M10 |

---

*This document is the single source of truth for the Gorakhpur KG project. Update it as architecture decisions change.*
