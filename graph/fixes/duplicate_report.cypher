/*
Read-only duplicate-report queries.
Run these to list duplicate primary IDs for core labels before any changes.

Usage (cypher-shell):
  cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD < graph/fixes/duplicate_report.cypher

Adjust LIMITs or LABEL/PROP lists as needed.
*/

// Candidates by candidate_id
MATCH (n:Candidate)
WHERE n.candidate_id IS NOT NULL
WITH n.candidate_id AS id, collect(n) AS nodes, size(collect(n)) AS cnt
WHERE cnt > 1
RETURN 'Candidate' AS label, id AS prop_value, cnt AS count, [x IN nodes | id(x)] AS node_ids
ORDER BY cnt DESC LIMIT 200;

// Parties by party_id
MATCH (n:Party)
WHERE n.party_id IS NOT NULL
WITH n.party_id AS id, collect(n) AS nodes, size(collect(n)) AS cnt
WHERE cnt > 1
RETURN 'Party' AS label, id AS prop_value, cnt AS count, [x IN nodes | id(x)] AS node_ids
ORDER BY cnt DESC LIMIT 200;

// Booths by booth_id
MATCH (n:Booth)
WHERE n.booth_id IS NOT NULL
WITH n.booth_id AS id, collect(n) AS nodes, size(collect(n)) AS cnt
WHERE cnt > 1
RETURN 'Booth' AS label, id AS prop_value, cnt AS count, [x IN nodes | id(x)] AS node_ids
ORDER BY cnt DESC LIMIT 200;

// PulseEvent duplicates by event_id
MATCH (n:PulseEvent)
WHERE n.event_id IS NOT NULL
WITH n.event_id AS id, collect(n) AS nodes, size(collect(n)) AS cnt
WHERE cnt > 1
RETURN 'PulseEvent' AS label, id AS prop_value, cnt AS count, [x IN nodes | id(x)] AS node_ids
ORDER BY cnt DESC LIMIT 200;

// Generic helper — run for any label/prop by replacing :Label and prop
// MATCH (n:Label) WHERE n.prop IS NOT NULL
// WITH n.prop AS id, collect(n) AS nodes, size(collect(n)) AS cnt
// WHERE cnt > 1 RETURN id, cnt, [x IN nodes | id(x)] AS node_ids LIMIT 200;
