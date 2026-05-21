/*
Per-label non-destructive dedupe for `Candidate` (uses same approach as apoc_safe_merge.cypher).
Run in cypher-shell (dry-run):
  cypher-shell -a bolt://localhost:7687 -u neo4j -p gorakhpur_neo4j_pass < graph/fixes/apoc_safe_merge_candidate.cypher
*/

//// MARK DUPLICATES (non-destructive)
MATCH (n:Candidate)
  WHERE n.candidate_id IS NOT NULL
  WITH n.candidate_id AS cid, collect(n) AS nodes, size(collect(n)) AS cnt
  WHERE cnt > 1
  UNWIND nodes AS d
  SET d:Duplicate
  WITH cid, nodes
  LIMIT 1000
  RETURN cid, size(nodes) AS dup_count, [x IN nodes | id(x)] AS node_ids
;

//// CREATE CANONICAL MAP (select canonical per candidate_id)
MATCH (n:Candidate)
  WHERE n.candidate_id IS NOT NULL
  WITH n.candidate_id AS cid, collect(n) AS nodes, size(collect(n)) AS cnt
  WHERE cnt > 1
  UNWIND nodes AS node
  WITH cid, nodes, node
  ORDER BY node.created_at ASC
  WITH cid, head(nodes) AS canonical, tail(nodes) AS duplicates
  RETURN cid, id(canonical) AS canonical_id, [d IN duplicates | id(d)] AS duplicate_ids
  LIMIT 100
;

//// REWIRE RELATIONSHIPS (create equivalent relationships on canonical)
MATCH (n:Candidate)
  WHERE n.candidate_id IS NOT NULL
  WITH n.candidate_id AS cid, collect(n) AS nodes
  WHERE size(nodes) > 1
  WITH cid, nodes, head(nodes) AS canonical, tail(nodes) AS duplicates
  UNWIND duplicates AS d

  CALL {
    WITH d, canonical
    MATCH (d)-[r]->(t)
    WITH d, canonical, r, t
      CALL apoc.merge.relationship(canonical, TYPE(r), {}, properties(r), t) YIELD rel
    RETURN count(*) AS out_rewired
  }

  CALL {
    WITH d, canonical
    MATCH (s)-[r]->(d)
    WITH s, r, canonical
      CALL apoc.merge.relationship(s, TYPE(r), {}, properties(r), canonical) YIELD rel
    RETURN count(*) AS in_rewired
  }

  SET d:Deprecated
  SET d.deprecated_at = datetime()
  SET d.rewired_to = id(canonical)
  RETURN cid, id(canonical) AS canonical_id, id(d) AS duplicate_id
  LIMIT 1000
;

//// DRY-RUN CHECK
MATCH (d:Deprecated)
RETURN count(d) AS deprecated_count, collect(d.candidate_id)[0..50] AS sample_candidate_ids;

/* Final merge (destructive) is intentionally omitted here. */
