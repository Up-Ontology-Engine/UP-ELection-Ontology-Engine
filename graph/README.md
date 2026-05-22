# Graph Maintenance — Knowledge Graph Helpers

This folder contains helper scripts and instructions to inspect and safely modify the Neo4j knowledge graph used by the UP-Election-Ontology-Engine.

Files added:

- `fixes/duplicate_report.cypher` — read-only Cypher queries to list duplicate primary IDs for core labels (Candidate, Party, Booth, PulseEvent).
- `fixes/apoc_safe_merge.cypher` — APOC-safe merge template with stepwise, non-destructive approach (mark, rewire, optional final merge).
- `validators/validate_graph.py` — validator to check node counts, duplicates, orphan pulse events, booths without AC link.
- `tools/run_duplicate_report.py` — Python helper that executes `duplicate_report.cypher` and writes a JSON report to `graph/reports/`.
- `tools/mark_orphan_pulseevents.py` — finds PulseEvent nodes with no `AT_BOOTH` relationship and (optionally) marks `is_orphan` in Postgres. Dry-run by default.

Recommended safe workflow
1. Backup Neo4j (neo4j-admin dump) and Postgres (pg_dump) before any change.
2. Run the graph validator:

```bash
source .venv/bin/activate
python -m graph.validators.validate_graph
```

3. Generate duplicate report JSON:

```bash
NEO4J_URI='neo4j://localhost:7687' NEO4J_USER='neo4j' NEO4J_PASSWORD='pw' \
  python graph/tools/run_duplicate_report.py
```

4. Inspect `graph/reports/duplicate_report_<ts>.json` and decide merge policy.

5. Find orphan PulseEvents and review:

```bash
NEO4J_URI='neo4j://localhost:7687' NEO4J_USER='neo4j' NEO4J_PASSWORD='pw' \
  POSTGRES_URL='postgresql://user:pw@host/db' python graph/tools/mark_orphan_pulseevents.py
```

6. If orphan list is acceptable, apply flags (after confirming Postgres backup):

```bash
... python graph/tools/mark_orphan_pulseevents.py --apply
```

7. Optionally proceed to non-destructive rewiring with `fixes/apoc_safe_merge.cypher` (follow comments and dry-run sections). Only run `apoc.refactor.mergeNodes` after full backup and sign-off.

Notes & prerequisites
- APOC plugin required on Neo4j for advanced refactor operations.
- Scripts expect environment variables: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, and `POSTGRES_URL` when needed.
- All scripts default to dry-run behaviour and write outputs into `graph/reports/` for review.

If you want, I can now run the duplicate report and orphan detection here if you provide Neo4j (and Postgres for orphan apply) credentials; otherwise run the commands above locally and paste the JSON outputs for me to analyze and propose the exact fix operations.
