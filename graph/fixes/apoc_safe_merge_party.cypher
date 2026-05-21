/* Per-label dedupe for `Party` */

MATCH (n:Party)
  WHERE n.party_id IS NOT NULL
  WITH n.party_id AS pid, collect(n) AS nodes, size(collect(n)) AS cnt
  WHERE cnt > 1
  UNWIND nodes AS d
  SET d:Duplicate
  WITH pid, nodes
  LIMIT 1000
  RETURN pid, size(nodes) AS dup_count, [x IN nodes | id(x)] AS node_ids
;

MATCH (n:Party)
  WHERE n.party_id IS NOT NULL
  WITH n.party_id AS pid, collect(n) AS nodes, size(collect(n)) AS cnt
  WHERE cnt > 1
  UNWIND nodes AS node
  WITH pid, nodes, node
  ORDER BY node.created_at ASC
  WITH pid, head(nodes) AS canonical, tail(nodes) AS duplicates
  RETURN pid, id(canonical) AS canonical_id, [d IN duplicates | id(d)] AS duplicate_ids
  LIMIT 100
;

MATCH (n:Party)
  WHERE n.party_id IS NOT NULL
  WITH n.party_id AS pid, collect(n) AS nodes
  WHERE size(nodes) > 1
  WITH pid, nodes, head(nodes) AS canonical, tail(nodes) AS duplicates
  UNWIND duplicates AS d

  CALL {
    WITH d, canonical
    MATCH (d)-[r]->(t)
    WITH d, canonical, r, t
    CALL apoc.merge.relationship(canonical, TYPE(r), {}, properties(r), t) YIELD rel
    RETURN count(rel) AS out_rewired
  }

  CALL {
    WITH d, canonical
    MATCH (s)-[r]->(d)
    WITH s, r, canonical
    CALL apoc.merge.relationship(s, TYPE(r), {}, properties(r), canonical) YIELD rel
    RETURN count(rel) AS in_rewired
  }

  SET d:Deprecated
  SET d.deprecated_at = datetime()
  SET d.rewired_to = id(canonical)
  RETURN pid, id(canonical) AS canonical_id, id(d) AS duplicate_id
  LIMIT 1000
;

MATCH (d:Deprecated)
RETURN count(d) AS deprecated_count, collect(d.party_id)[0..50] AS sample_party_ids;
