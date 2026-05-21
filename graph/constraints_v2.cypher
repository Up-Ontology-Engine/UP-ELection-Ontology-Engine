// =============================================================================
// Gorakhpur KG — Neo4j Constraints v2: Intelligence Layer Nodes
// Ontology version: 1.0.0-ontology-phase
//
// Run after constraints.cypher:
//   cat graph/constraints_v2.cypher | cypher-shell -u neo4j -p <password>
//
// NODE KEY constraints require Neo4j Enterprise or AuraDB.
// Canonical ontology spec: docs/ontology_spec.md
// =============================================================================

// ── Additional uniqueness constraints (Community Edition safe) ────────────────
// These complement constraints.cypher with ontology v2 entity classes.

CREATE CONSTRAINT IF NOT EXISTS FOR (s:State)              REQUIRE s.state_id     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:District)           REQUIRE d.district_id  IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (ds:DemographicSegment) REQUIRE ds.segment_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (ga:GovernanceAsset)   REQUIRE ga.asset_id    IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (ts:TwinScenario)      REQUIRE ts.scenario_id IS UNIQUE;

// ── NODE KEY constraints (Enterprise / AuraDB only) ───────────────────────────
// Uncomment after confirming Neo4j edition supports NODE KEY.

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
CREATE INDEX IF NOT EXISTS FOR (dq:DataQuality) ON (dq.computed_at);

// Narrative
CREATE INDEX IF NOT EXISTS FOR (n:Narrative) ON (n.booth_id);
CREATE INDEX IF NOT EXISTS FOR (n:Narrative) ON (n.narrative_type);
CREATE INDEX IF NOT EXISTS FOR (n:Narrative) ON (n.strength);
CREATE INDEX IF NOT EXISTS FOR (n:Narrative) ON (n.computed_at);

// SchemeGap
CREATE INDEX IF NOT EXISTS FOR (sg:SchemeGap) ON (sg.booth_id);
CREATE INDEX IF NOT EXISTS FOR (sg:SchemeGap) ON (sg.gap_type);
CREATE INDEX IF NOT EXISTS FOR (sg:SchemeGap) ON (sg.priority);
CREATE INDEX IF NOT EXISTS FOR (sg:SchemeGap) ON (sg.scheme_name);
CREATE INDEX IF NOT EXISTS FOR (sg:SchemeGap) ON (sg.computed_at);

// ContradictionFlag
CREATE INDEX IF NOT EXISTS FOR (cf:ContradictionFlag) ON (cf.booth_id);
CREATE INDEX IF NOT EXISTS FOR (cf:ContradictionFlag) ON (cf.entity);
CREATE INDEX IF NOT EXISTS FOR (cf:ContradictionFlag) ON (cf.flag_label);
CREATE INDEX IF NOT EXISTS FOR (cf:ContradictionFlag) ON (cf.delta);
CREATE INDEX IF NOT EXISTS FOR (cf:ContradictionFlag) ON (cf.computed_at);

// DemographicSegment
CREATE INDEX IF NOT EXISTS FOR (ds:DemographicSegment) ON (ds.segment_type);
CREATE INDEX IF NOT EXISTS FOR (ds:DemographicSegment) ON (ds.ac_id);

// GovernanceAsset
CREATE INDEX IF NOT EXISTS FOR (ga:GovernanceAsset) ON (ga.booth_id);
CREATE INDEX IF NOT EXISTS FOR (ga:GovernanceAsset) ON (ga.asset_type);

// TwinScenario
CREATE INDEX IF NOT EXISTS FOR (ts:TwinScenario) ON (ts.ac_id);
CREATE INDEX IF NOT EXISTS FOR (ts:TwinScenario) ON (ts.scenario_type);
CREATE INDEX IF NOT EXISTS FOR (ts:TwinScenario) ON (ts.created_at);

// ── Canonical relationship taxonomy (see docs/ontology_spec.md) ───────────────
// :State          -[:HAS_DISTRICT]->          :District
// :District       -[:HAS_AC]->                :AssemblyConstituency
// :AssemblyConstituency -[:HAS_BOOTH]->       :Booth
// :Booth          -[:IN_AC]->                 :AssemblyConstituency
// :PulseEvent     -[:AT_BOOTH]->              :Booth
// :PulseEvent     -[:ABOUT_ISSUE]->           :Issue
// :PulseEvent     -[:MENTIONS]->              :Party | :Candidate
// :Candidate      -[:MEMBER_OF]->             :Party
// :Candidate      -[:CONTESTED_IN]->          :AssemblyConstituency
// :Candidate      -[:WON_IN]->                :AssemblyConstituency
// :Booth          -[:HAS_QUALITY]->           :DataQuality
// :Booth          -[:HAS_NARRATIVE]->         :Narrative
// :Narrative      -[:ABOUT_ISSUE]->           :Issue
// :Narrative      -[:INVOLVES_PARTY]->        :Party
// :Narrative      -[:INVOLVES_CANDIDATE]->    :Candidate
// :Booth          -[:HAS_SCHEME_GAP]->        :SchemeGap
// :SchemeGap      -[:FOR_SCHEME]->            :Scheme
// :SchemeGap      -[:TAGGED_ISSUE]->          :Issue
// :Booth          -[:HAS_CONTRADICTION]->     :ContradictionFlag
// :ContradictionFlag -[:ABOUT_ENTITY]->       :Party | :Candidate
// :AssemblyConstituency -[:HAS_SCENARIO]->    :TwinScenario
// :TwinScenario   -[:TARGETS_BOOTH]->         :Booth
// :Booth          -[:IN_SEGMENT]->            :DemographicSegment
// :Booth          -[:HAS_GOVERNANCE_ASSET]->  :GovernanceAsset
