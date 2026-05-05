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
