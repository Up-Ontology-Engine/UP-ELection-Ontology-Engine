// =============================================================================
// Gorakhpur KG — Neo4j Constraints v2: Intelligence Layer Nodes
// Run after constraints.cypher:
//   cat graph/constraints_v2.cypher | cypher-shell -u neo4j -p <password>
// =============================================================================

// ── Uniqueness constraints ────────────────────────────────────────────────────

// DataQuality: one record per booth per compute window
CREATE CONSTRAINT IF NOT EXISTS FOR (dq:DataQuality)
    REQUIRE (dq.booth_id, dq.computed_at) IS NODE KEY;

// Narrative: one narrative type per booth per compute window
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Narrative)
    REQUIRE (n.booth_id, n.narrative_type, n.computed_at) IS NODE KEY;

// SchemeGap: one gap record per booth+scheme per compute window
CREATE CONSTRAINT IF NOT EXISTS FOR (sg:SchemeGap)
    REQUIRE (sg.booth_id, sg.scheme_name, sg.computed_at) IS NODE KEY;

// ContradictionFlag: one flag per booth+entity+source pair per window
CREATE CONSTRAINT IF NOT EXISTS FOR (cf:ContradictionFlag)
    REQUIRE (cf.booth_id, cf.entity, cf.source_a, cf.source_b, cf.computed_at) IS NODE KEY;

// ── Performance indexes ───────────────────────────────────────────────────────

// DataQuality
CREATE INDEX IF NOT EXISTS FOR (dq:DataQuality) ON (dq.booth_id);
CREATE INDEX IF NOT EXISTS FOR (dq:DataQuality) ON (dq.quality_label);
CREATE INDEX IF NOT EXISTS FOR (dq:DataQuality) ON (dq.overall_quality_score);

// Narrative
CREATE INDEX IF NOT EXISTS FOR (n:Narrative) ON (n.booth_id);
CREATE INDEX IF NOT EXISTS FOR (n:Narrative) ON (n.narrative_type);
CREATE INDEX IF NOT EXISTS FOR (n:Narrative) ON (n.strength);

// SchemeGap
CREATE INDEX IF NOT EXISTS FOR (sg:SchemeGap) ON (sg.booth_id);
CREATE INDEX IF NOT EXISTS FOR (sg:SchemeGap) ON (sg.gap_type);
CREATE INDEX IF NOT EXISTS FOR (sg:SchemeGap) ON (sg.priority);
CREATE INDEX IF NOT EXISTS FOR (sg:SchemeGap) ON (sg.scheme_name);

// ContradictionFlag
CREATE INDEX IF NOT EXISTS FOR (cf:ContradictionFlag) ON (cf.booth_id);
CREATE INDEX IF NOT EXISTS FOR (cf:ContradictionFlag) ON (cf.entity);
CREATE INDEX IF NOT EXISTS FOR (cf:ContradictionFlag) ON (cf.flag_label);
CREATE INDEX IF NOT EXISTS FOR (cf:ContradictionFlag) ON (cf.delta);

// ── Relationship type hints (documentation only) ──────────────────────────────
// :Booth -[:HAS_QUALITY]->        :DataQuality
// :Booth -[:HAS_NARRATIVE]->      :Narrative
// :Narrative -[:ABOUT_ISSUE]->    :Issue
// :Narrative -[:INVOLVES_PARTY]-> :Party
// :Narrative -[:INVOLVES_CANDIDATE]-> :Candidate
// :Booth -[:HAS_SCHEME_GAP]->     :SchemeGap
// :SchemeGap -[:FOR_SCHEME]->     :Scheme
// :SchemeGap -[:TAGGED_ISSUE]->   :Issue
// :Booth -[:HAS_CONTRADICTION]->  :ContradictionFlag
// :ContradictionFlag -[:ABOUT_ENTITY]-> :Party | :Candidate
