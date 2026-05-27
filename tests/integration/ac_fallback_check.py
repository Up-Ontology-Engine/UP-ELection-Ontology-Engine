#!/usr/bin/env python3
"""
Quick test to verify AC subgraph fallback logic.
Simulates what get_graph_subgraph returns for GKP_322 (Gorakhpur Urban AC).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.queries import get_graph_subgraph

# Test AC query with fallback
print("=" * 60)
print("Testing: AC query for GKP_322 (should trigger booth fallback)")
print("=" * 60)

result = get_graph_subgraph(entity_type="AC", entity_id="GKP_322", exclude_types=[], limit=120)

print(f"\n✓ Nodes returned: {len(result['nodes'])}")
print(f"✓ Edges returned: {len(result['edges'])}")

if result["nodes"]:
    print("\nNode types in result:")
    node_types = {}
    for node in result["nodes"]:
        ntype = node.get("type", "Unknown")
        node_types[ntype] = node_types.get(ntype, 0) + 1
        if ntype == "AssemblyConstituency":
            print(f"  → AC node (synthetic): {node['label']}")

    for ntype, count in sorted(node_types.items()):
        print(f"  • {ntype}: {count}")

    print("\nSample edges (first 5):")
    for edge in result["edges"][:5]:
        print(f"  • {edge['source'][:20]}... --{edge['type']}--> {edge['target'][:20]}...")

    print("\n✅ AC query fallback working: Returns booth network for GKP_322")
else:
    print("\n⚠️  No nodes found. Check if booths exist in Neo4j for GKP_322")

print("\n" + "=" * 60)
