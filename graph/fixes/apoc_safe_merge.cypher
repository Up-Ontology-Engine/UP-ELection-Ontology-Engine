/*
APOC-safe merge template (DRY RUN first).

This file contains a stepwise, non-destructive approach to deduplicating nodes
with APOC available. It intentionally separates discovery, marking, rewiring,
and final merge so you can review intermediate state. DO NOT RUN the final
`apoc.refactor.mergeNodes` block until you have backups.

Steps:
  1) Run duplicate_report.cypher and inspect duplicates.
  2) Run the MARK DUPLICATES block (adds :Duplicate label and records candidates).
  3) Run the REWIRE block (rewires relationships from duplicates to canonical nodes, keeping duplicates intact and tagged).
  4) Review results and re-run validator.
  5) OPTIONAL: Run FINAL MERGE block to compact nodes (destructive). Keep backups first.

Notes:
  - Requires APOC plugin for `apoc.refactor.mergeNodes` (if using final merge).
  - Always export affected nodes before writing: apoc.export.csv.query or neo4j-admin dump.
*/

/////////////////////////
// PARAMETERS / HELP
/////////////////////////
// Replace LABEL and KEY_PROP for the entity you want to dedupe.
// Example: :Candidate and candidate_id
// Set LIMIT to a reasonable number for dry runs.
// You can run this file multiple times for different labels.

// ====== MARK DUPLICATES (non-destructive) ======
// This marks all duplicate nodes with :Duplicate and records node ids in a property
// for quick review. It does NOT change relationships or merge nodes.

CALL {
  MATCH (n:Candidate)
  WHERE n.candidate_id IS NOT NULL
  WITH n.candidate_id AS cid, collect(n) AS nodes, size(collect(n)) AS cnt
  WHERE cnt > 1
  UNWIND nodes AS d
  SET d:Duplicate
  WITH cid, nodes
  LIMIT 1000
  RETURN cid, size(nodes) AS dup_count, [x IN nodes | id(x)] AS node_ids
};

// ====== CREATE CANONICAL MAP (select canonical id per group) ======
// Strategy: pick the node with the earliest created_at (if present), else first.
// This creates a mapping in-memory; you can export it via APOC if needed.

CALL {
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
};

// ====== REWIRE RELATIONSHIPS (safe, non-destructive) ======
// For each duplicate node, copy/merge relationships to the canonical node, then tag duplicate as deprecated.

// NOTE: This block uses MERGE to create equivalent relationships from source->canonical.
// It preserves the duplicate node for audit and rollback.

CALL {
  MATCH (n:Candidate)
  WHERE n.candidate_id IS NOT NULL
  WITH n.candidate_id AS cid, collect(n) AS nodes
  WHERE size(nodes) > 1
  WITH cid, nodes, head(nodes) AS canonical, tail(nodes) AS duplicates
  UNWIND duplicates AS d

  // Outgoing relationships from duplicate -> target
  CALL {
    WITH d, canonical
    MATCH (d)-[r]->(t)
    WITH d, canonical, r, t
    // create same relationship from canonical to the target if not exists using APOC
    CALL apoc.merge.relationship(canonical, TYPE(r), {}, properties(r), t) YIELD rel
    RETURN count(rel) AS out_rewired
  }

  // Incoming relationships from source -> duplicate
  CALL {
    WITH d, canonical
    MATCH (s)-[r]->(d)
    WITH s, r, canonical
    CALL apoc.merge.relationship(s, TYPE(r), {}, properties(r), canonical) YIELD rel
    RETURN count(rel) AS in_rewired
  }

  // mark duplicate node for review
  SET d:Deprecated
  SET d.deprecated_at = datetime()
  SET d.rewired_to = id(canonical)
  RETURN cid, id(canonical) AS canonical_id, id(d) AS duplicate_id
  LIMIT 1000
};

// ====== DRY-RUN CHECK: list tagged duplicates and rewired counts ======
MATCH (d:Deprecated)
RETURN count(d) AS deprecated_count, collect(d.candidate_id) AS sample_candidate_ids LIMIT 50;

// ====== FINAL MERGE (DESTRUCTIVE) ======
// WARNING: This operation merges nodes physically and can be hard to reverse.
// Keep it commented out until you have backups and confirmed rewiring.

/*
CALL {
  MATCH (n:Candidate)
  WHERE n.candidate_id IS NOT NULL
  WITH n.candidate_id AS cid, collect(n) AS nodes
  WHERE size(nodes) > 1
  WITH cid, nodes
  // choose canonical by created_at or first
  WITH cid, nodes, head(nodes) AS canonical, tail(nodes) AS duplicates
  CALL apoc.refactor.mergeNodes([canonical] + duplicates, {properties:'combine', mergeRels:true}) YIELD node
  SET node.merged_on = datetime()
  RETURN cid, id(node) AS merged_node_id
  LIMIT 200
}
*/

// ====== BACKOUT TIP ======
// If you ran the final merge and need to restore, you must restore from a Neo4j dump
// or from exported CSVs created prior to running this script. Keep evidence files
// of id mappings (canonical -> duplicate ids) to help manual recovery.
