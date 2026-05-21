"""Graph validation utilities for the Gorakhpur KG.

Run this script to sanity-check the Neo4j knowledge graph after loads.

Usage:
  python -m graph.validators.validate_graph

Checks performed:
- Node counts for core labels
- Duplicate ID values for primary identifier properties
- Orphan PulseEvent nodes (no AT_BOOTH relationship)
- Booth nodes not attached to any AC
"""
from __future__ import annotations

from api.db import get_neo4j_session
from neo4j import exceptions as neo4j_exceptions

LABEL_KEY_MAP = {
    "State": ("state_id",),
    "District": ("district_id",),
    "AssemblyConstituency": ("ac_id",),
    "Booth": ("booth_id",),
    "Issue": ("code",),
    "Candidate": ("candidate_id",),
    "Party": ("party_id",),
}


def _count_nodes(session, label: str) -> int:
    r = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()
    return int(r["c"]) if r else 0


def _find_duplicate_ids(session, label: str, prop: str) -> list[tuple[str, int]]:
    q = (
        f"MATCH (n:{label}) WHERE n.{prop} IS NOT NULL "
        f"WITH n.{prop} as id, count(*) as c WHERE c > 1 RETURN id, c LIMIT 50"
    )
    result = session.run(q)
    return [(r["id"], int(r["c"])) for r in result]


def _count_orphan_pulse_events(session) -> int:
    r = session.run(
        "MATCH (pe:PulseEvent) "
        "WHERE NOT EXISTS { MATCH (pe)-[r]->(:Booth) WHERE type(r) = 'AT_BOOTH' } "
        "RETURN count(pe) AS c"
    ).single()
    return int(r["c"]) if r else 0


def _count_booths_without_ac(session) -> int:
    r = session.run(
        "MATCH (b:Booth) WHERE NOT (:AssemblyConstituency)-[:HAS_BOOTH]->(b) RETURN count(b) AS c"
    ).single()
    return int(r["c"]) if r else 0


def run_checks() -> dict:
    results = {}
    with get_neo4j_session() as session:
        # Node counts
        node_counts = {lbl: _count_nodes(session, lbl) for lbl in LABEL_KEY_MAP.keys()}
        results["node_counts"] = node_counts

        # Duplicate ID checks
        dupes = {}
        for lbl, keys in LABEL_KEY_MAP.items():
            for k in keys:
                found = _find_duplicate_ids(session, lbl, k)
                if found:
                    dupes.setdefault(lbl, {})[k] = found
        results["duplicates"] = dupes

        # Orphan pulse events
        results["orphan_pulse_events"] = _count_orphan_pulse_events(session)

        # Booths missing AC link
        results["booths_without_ac"] = _count_booths_without_ac(session)

    return results


def pretty_print(res: dict) -> None:
    print("\n=== Graph Validation Summary ===\n")
    nc = res.get("node_counts", {})
    print("Node counts:")
    for k, v in nc.items():
        print(f" - {k}: {v}")

    print("\nDuplicate ID issues (sample):")
    dup = res.get("duplicates", {})
    if not dup:
        print(" - No duplicate primary IDs found")
    else:
        for lbl, props in dup.items():
            print(f" - {lbl}:")
            for prop, rows in props.items():
                for val, cnt in rows:
                    print(f"    * {prop} = {val} (count={cnt})")

    print("\nOrphan pulse events (no AT_BOOTH):", res.get("orphan_pulse_events", 0))
    print("Booths without AC link:", res.get("booths_without_ac", 0))
    print("\n=== End summary ===\n")


if __name__ == "__main__":
    print("Running graph validation checks...")
    try:
        r = run_checks()
        pretty_print(r)
    except RuntimeError as e:
        print("Error:", e)
        print(
            "Ensure environment variables are set: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD"
        )
        print("Example:")
        print(
            "NEO4J_URI='neo4j://localhost:7687' NEO4J_USER='neo4j' NEO4J_PASSWORD='yourpw' python -m graph.validators.validate_graph"
        )
        raise
    except neo4j_exceptions.AuthError:
        print("Authentication failed when connecting to Neo4j.")
        print(" - Verify NEO4J_USER and NEO4J_PASSWORD are correct.")
        print(" - Verify the Neo4j server at NEO4J_URI is running and reachable.")
        print(" - You can test with: cypher-shell -u <user> -p <pass> -a <host:port>")
        raise
    except Exception as e:
        print("Unexpected error while validating graph:", e)
        raise
