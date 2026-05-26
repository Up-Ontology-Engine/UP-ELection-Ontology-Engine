// =============================================================================
// Gorakhpur KG — Neo4j Constraints & Indexes
// Run once on a fresh Neo4j instance:
//   cat graph/constraints.cypher | cypher-shell -u neo4j -p <password>
// =============================================================================

// ── Uniqueness constraints ────────────────────────────────────────────────────
CREATE CONSTRAINT IF NOT EXISTS FOR (s:State)                   REQUIRE s.name     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:District)                REQUIRE d.name     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (a:AssemblyConstituency)    REQUIRE a.ac_id    IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (b:Booth)                   REQUIRE b.booth_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (b:Booth)                   REQUIRE b.id       IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (c:Candidate)               REQUIRE c.candidate_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Party)                   REQUIRE p.party_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Party)                   REQUIRE p.name     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Election)                REQUIRE e.election_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:Issue)                   REQUIRE i.code     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (sc:Scheme)                 REQUIRE sc.name    IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (pan:Panchayat)             REQUIRE pan.panchayat_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (pe:PulseEvent)             REQUIRE pe.event_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (w:WorkItem)                REQUIRE w.work_id   IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (v:YouTubeVideo)            REQUIRE v.video_id  IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (ch:Channel)                REQUIRE ch.channel_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (cr:CriminalRecord)         REQUIRE cr.record_id  IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (ad:AssetDeclaration)       REQUIRE ad.decl_id    IS UNIQUE;


// ── Performance indexes ───────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS FOR (b:Booth)      ON (b.ac_id);
CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.mapped_booth_id);
CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.mapped_ac_id);
CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.issue);
CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.entity);
CREATE INDEX IF NOT EXISTS FOR (pe:PulseEvent) ON (pe.created_at);
CREATE INDEX IF NOT EXISTS FOR (c:Candidate)  ON (c.ac_id);
CREATE INDEX IF NOT EXISTS FOR (c:Candidate)  ON (c.party);
CREATE INDEX IF NOT EXISTS FOR (v:YouTubeVideo)     ON (v.views);
CREATE INDEX IF NOT EXISTS FOR (v:YouTubeVideo)     ON (v.query_source);
CREATE INDEX IF NOT EXISTS FOR (cr:CriminalRecord)  ON (cr.candidate_id);
CREATE INDEX IF NOT EXISTS FOR (ad:AssetDeclaration) ON (ad.candidate_id);
CREATE INDEX IF NOT EXISTS FOR (c:Candidate)        ON (c.criminal_cases);
CREATE INDEX IF NOT EXISTS FOR (c:Candidate)        ON (c.net_worth_cr);
