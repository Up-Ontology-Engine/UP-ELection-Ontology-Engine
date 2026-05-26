// Voter-level knowledge graph — constraints & indexes
// Ported from digital-democracy-pipeline (neo4j_ingest._CONSTRAINTS), adapted to
// hang under the existing Booth / AssemblyConstituency hierarchy.
//
// Run: cat graph/constraints_voter.cypher | cypher-shell -u neo4j -p $NEO4J_PASSWORD
// (load_voter_graph.py also applies these automatically on ingest.)

CREATE CONSTRAINT voter_key   IF NOT EXISTS FOR (v:Voter)      REQUIRE v.voter_key IS UNIQUE;
CREATE CONSTRAINT person_id    IF NOT EXISTS FOR (p:Person)     REQUIRE p.id IS UNIQUE;

CREATE INDEX voter_epic        IF NOT EXISTS FOR (v:Voter)      ON (v.epic_id);
CREATE INDEX voter_norm        IF NOT EXISTS FOR (v:Voter)      ON (v.name_norm);
CREATE INDEX voter_booth       IF NOT EXISTS FOR (v:Voter)      ON (v.booth_id);
CREATE INDEX household_id      IF NOT EXISTS FOR (h:Household)  ON (h.id);
CREATE INDEX section_id        IF NOT EXISTS FOR (s:Section)    ON (s.id);

CREATE FULLTEXT INDEX voter_name IF NOT EXISTS FOR (v:Voter) ON EACH [v.name, v.name_roman];
