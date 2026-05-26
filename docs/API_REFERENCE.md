# API Reference Specification

This document lists the endpoint specifications, request payloads, response schemas, and authentication mappings for the UP Vidhan Sabha Election Ontology Engine backend API.

---

## Global API Schema Configurations

-   **Base URL:**
    -   *Local Development:* `http://localhost:8000`
    -   *Production Gateway:* `https://api.election-engine.internal`
-   **Content-Type:** `application/json` for all payloads.
-   **Error Responses:** Standardized JSON error schema:
    ```json
    {
      "detail": "Error message description string"
    }
    ```

---

## 1. System Operations Endpoints

### GET `/health`
Returns the status of relational databases, graph databases, and cache dependencies. Used for Kubernetes liveness and readiness probes.

*   **Authentication:** None.
*   **Success Response (200 OK):**
    ```json
    {
      "status": "healthy",
      "postgres": "connected",
      "neo4j": "connected",
      "redis": "connected",
      "elapsed_ms": 12.4
    }
    ```
*   **Error Response (503 Service Unavailable):**
    ```json
    {
      "status": "unhealthy",
      "postgres": "connected",
      "neo4j": "disconnected",
      "redis": "connected",
      "elapsed_ms": 145.2
    }
    ```

---

## 2. Booth & AC Intelligence Endpoints

### GET `/ac/{ac_id}/booths`
Fetches a list of polling booths for a given Assembly Constituency (AC) with their corresponding computed political leans and data quality levels.

*   **Parameters:**
    *   `ac_id` (Path, Required): AC code string (e.g., `GKP_322`).
    *   `lean` (Query, Optional): Filter by political lean (e.g., `STRONG_BJP`, `LEAN_OPP`).
    *   `min_quality` (Query, Optional): Minimum data quality score filter (float, 0.0 to 1.0).
*   **Success Response (200 OK):**
    ```json
    [
      {
        "booth_id": "GKP_U_001",
        "booth_name": "Primary School Building Room 1",
        "bjp_pulse": 0.45,
        "opp_pulse": -0.12,
        "digital_lean": "LEAN_BJP",
        "overall_quality_score": 0.82
      }
    ]
    ```

### GET `/booth/{id}/summary`
Fetches the compiled 10-panel profile for an individual booth, aggregating demographics, historical results, narratives, scheme gaps, and contradictions.

*   **Parameters:**
    *   `id` (Path, Required): Polling booth identifier (e.g., `GKP_U_045`).
*   **Success Response (200 OK):**
    ```json
    {
      "booth_id": "GKP_U_045",
      "booth_name": "Junior High School North Wing",
      "demographics": {
        "total_voters": 1240,
        "male_ratio": 0.54,
        "female_ratio": 0.46,
        "age_segments": {
          "18-25": 140,
          "26-45": 620,
          "46+": 480
        }
      },
      "historical_results": [
        {
          "election_year": 2022,
          "winner_party": "BJP",
          "winner_votes": 680,
          "margin": 120
        }
      ],
      "top_issues": [
        {
          "issue_code": "water",
          "mentions": 34,
          "polarity": -0.42
        }
      ],
      "scheme_gaps": [
        {
          "scheme_name": "PMAY-G",
          "gap_type": "execution_gap",
          "priority": "HIGH"
        }
      ],
      "narratives": [
        {
          "narrative_type": "anti_incumbency",
          "strength": 0.72
        }
      ],
      "contradictions": [
        {
          "entity": "BJP",
          "delta": 0.8,
          "flag_label": "SWING_INDICATOR"
        }
      ]
    }
    ```

---

## 3. Interactive AI Reasoning Endpoints

### POST `/reasoning/query`
Processes natural language questions into structured graph database translations and web searches, producing a synthesized semantic response.

*   **Request Body:**
    ```json
    {
      "query": "Which booths show negative sentiment on electricity schemes?",
      "session_id": "8a3d7b92-fc14-41d9-813c-0c151cdbc42e"
    }
    ```
*   **Success Response (200 OK):**
    ```json
    {
      "answer": "Negative sentiment on electricity schemes is concentrated in three main booths (GKP_U_012, GKP_U_014, GKP_U_023). Relational data indicates completed schemes but sentiment is negative, suggesting an execution gap.",
      "generated_cypher": "MATCH (b:Booth)-[r:HAS_SCHEME_GAP]->(g:SchemeGap) WHERE g.scheme_name = 'Saubhagya' RETURN b.booth_id, g.gap_type",
      "graph_results": [
        {
          "booth_id": "GKP_U_012",
          "gap_type": "execution_gap"
        }
      ],
      "web_sources": [
        {
          "title": "Gorakhpur Power Infrastructure Report 2025",
          "url": "https://example.com/reports/gorakhpur-power"
        }
      ],
      "elapsed_ms": 845.2
    }
    ```
