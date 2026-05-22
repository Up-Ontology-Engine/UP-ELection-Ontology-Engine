# UP Election Ontology Specification
**Version:** 1.0.0-ontology-phase  
**Project:** UP Election Ontology Engine — Gorakhpur Urban AC  
**Date:** 2026-05-21  
**Status:** Phase 0 — Freeze in Progress

---

## 1. Entity Class Definitions

| Class | Primary Key | Example ID | Description |
|---|---|---|---|
| `State` | `state_id` | `UP` | Top-level administrative unit |
| `District` | `district_id` | `GKP` | District within a state |
| `AssemblyConstituency` | `ac_id` | `GKP_URBAN` | Vidhan Sabha segment (primary analysis unit) |
| `Booth` | `booth_id` | `GKP_322_001` | Individual polling booth (atomic data unit) |
| `Candidate` | `candidate_id` | `GKP_CAN_2022_001` | Contesting candidate |
| `Party` | `party_id` | `BJP` | Political party |
| `Issue` | `issue_code` | `water_supply` | Political/civic issue |
| `Scheme` | `scheme_id` | `PM_UJJWALA` | Government welfare scheme |
| `Panchayat` | `panchayat_id` | `PNCH_GKP_001` | Rural Panchayat body |
| `PulseEvent` | `event_id` | `PE_NEWS_abc123` | Digitally-observed political event |
| `Narrative` | `(booth_id, narrative_type, computed_at)` | composite | Detected narrative pattern |
| `DataQuality` | `(booth_id, computed_at)` | composite | Data quality metrics |
| `SchemeGap` | `(booth_id, scheme_name, computed_at)` | composite | Scheme delivery gap |
| `ContradictionFlag` | `(booth_id, entity, source_a, source_b, computed_at)` | composite | Cross-source signal conflict |
| `DemographicSegment` | `segment_id` | `SEG_YOUTH_VOLATILE` | Derived voter segment |
| `GovernanceAsset` | `asset_id` | `ROAD_001` | Physical governance delivery |
| `TwinScenario` | `scenario_id` | `SCN_WATER_2024` | Hypothetical intervention model |

---

## 2. ID Normalization Standard

All IDs use uppercase with underscore delimiters. No spaces, no special characters except `_`.

| Entity | Format | Example |
|---|---|---|
| State | `<STATE_CODE>` | `UP` |
| District | `<DIST_CODE>` | `GKP` |
| AC | `<DIST>_<LOCALITY>` | `GKP_URBAN` |
| Booth | `<DIST>_<AC_NUMBER>_<BOOTH_3DIGIT>` | `GKP_322_001` |
| Candidate | `<DIST>_CAN_<YEAR>_<SEQ_3DIGIT>` | `GKP_CAN_2022_001` |
| PulseEvent | `PE_<SOURCE>_<HASH8>` | `PE_NEWS_a1b2c3d4` |
| Scheme | `SCHEME_<NAME_UPPER>` | `SCHEME_PM_UJJWALA` |
| TwinScenario | `SCN_<TYPE>_<YEAR>` | `SCN_WATER_2024` |
| DemographicSegment | `SEG_<SEGMENT_TYPE>` | `SEG_YOUTH_VOLATILE` |

**Validation rule:** `booth_id` must match regex `^[A-Z]+_[0-9]+_[0-9]{3}$`

---

## 3. Relationship Taxonomy

All relationships are directed. Arrowhead points from source to target.

| From | Relationship | To | Notes |
|---|---|---|---|
| `State` | `HAS_DISTRICT` | `District` | |
| `District` | `HAS_AC` | `AssemblyConstituency` | |
| `AssemblyConstituency` | `HAS_BOOTH` | `Booth` | |
| `Booth` | `IN_AC` | `AssemblyConstituency` | Inverse of HAS_BOOTH |
| `PulseEvent` | `AT_BOOTH` | `Booth` | |
| `PulseEvent` | `ABOUT_ISSUE` | `Issue` | |
| `PulseEvent` | `MENTIONS` | `Party` | |
| `PulseEvent` | `MENTIONS` | `Candidate` | |
| `Candidate` | `MEMBER_OF` | `Party` | |
| `Candidate` | `CONTESTED_IN` | `AssemblyConstituency` | |
| `Candidate` | `WON_IN` | `AssemblyConstituency` | Optional, if winner |
| `Booth` | `HAS_QUALITY` | `DataQuality` | |
| `Booth` | `HAS_NARRATIVE` | `Narrative` | |
| `Narrative` | `ABOUT_ISSUE` | `Issue` | |
| `Narrative` | `INVOLVES_PARTY` | `Party` | |
| `Narrative` | `INVOLVES_CANDIDATE` | `Candidate` | |
| `Booth` | `HAS_SCHEME_GAP` | `SchemeGap` | |
| `SchemeGap` | `FOR_SCHEME` | `Scheme` | |
| `SchemeGap` | `TAGGED_ISSUE` | `Issue` | |
| `Booth` | `HAS_CONTRADICTION` | `ContradictionFlag` | |
| `ContradictionFlag` | `ABOUT_ENTITY` | `Party \| Candidate` | |
| `AssemblyConstituency` | `HAS_SCENARIO` | `TwinScenario` | |
| `TwinScenario` | `TARGETS_BOOTH` | `Booth` | |
| `Booth` | `IN_SEGMENT` | `DemographicSegment` | |
| `Booth` | `HAS_GOVERNANCE_ASSET` | `GovernanceAsset` | |

---

## 4. Semantic Rules

1. **Mandatory links:** Every `PulseEvent` must have `AT_BOOTH`. Every `SchemeGap` must have `FOR_SCHEME`. Every `Narrative` must have `ABOUT_ISSUE`.
2. **Orphan prevention:** No `PulseEvent`, `Narrative`, `SchemeGap`, or `ContradictionFlag` may exist without a parent `Booth`.
3. **ID uniqueness:** `booth_id` must be globally unique. `ac_id` must be globally unique.
4. **Temporal windows:** `DataQuality`, `Narrative`, `SchemeGap`, `ContradictionFlag` use `computed_at` timestamps. Never overwrite — always create new versioned records.
5. **Confidence thresholds:** `PulseEvent.nlp_confidence < 0.4` must not be loaded into the graph without a `DRAFT` flag.
6. **Party normalization:** "BJP" and "भाजपा" must map to the same `Party` node.

---

## 5. Ontology Versioning

The ontology version is stored in two places:
- Environment variable: `ONTOLOGY_VERSION=1.0.0`
- Database: `SELECT value FROM metadata WHERE key = 'ontology_version'`

On load, loaders must check `ONTOLOGY_VERSION` compatibility before writing nodes.

---

## 6. Constraint Activation Checklist

Run in order:

```cypher
-- Phase 1: Basic uniqueness (safe on Community Edition)
CREATE CONSTRAINT IF NOT EXISTS FOR (s:State) REQUIRE s.state_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:District) REQUIRE d.district_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (a:AssemblyConstituency) REQUIRE a.ac_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (b:Booth) REQUIRE b.booth_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Party) REQUIRE p.party_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (c:Candidate) REQUIRE c.candidate_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:Issue) REQUIRE i.issue_code IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (sc:Scheme) REQUIRE sc.scheme_id IS UNIQUE;

-- Phase 2: NODE KEY constraints (Enterprise/AuraDB only)
-- Run graph/constraints_v2.cypher after commenting these in
```

---

## 7. Ontology Sign-Off Gate

Before advancing to Phase 1 (Graph Hardening):

- [ ] All entity classes reviewed by data lead
- [ ] ID format validated against existing `booth_id` values in Postgres
- [ ] Relationship directions approved (confirm HAS_BOOTH vs IN_AC preference)
- [ ] Constraint script tested on staging Neo4j
- [ ] `ontology_version` env variable set in all services
