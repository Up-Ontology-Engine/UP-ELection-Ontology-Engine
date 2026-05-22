# Knowledge Graph AC Query Fallback Fix

## Problem
When querying the Knowledge Graph for AC (AssemblyConstituency) node "GKP_322", the frontend showed:
```
No graph data found for AC 'GKP_322'. Try removing type filters or check the entity ID.
```

This occurred because:
- Neo4j query `MATCH (center:AssemblyConstituency {ac_id: "GKP_322"})` returned 0 results
- No fallback mechanism existed for missing AC nodes
- User sees blank graph despite data existing at booth level

## Solution

### Backend Fix: api/queries.py (get_graph_subgraph)

**New fallback logic for AC queries:**

1. **Primary Query**: Try standard Neo4j query for AssemblyConstituency node
2. **Fallback Query** (if 0 results for AC type):
   ```cypher
   MATCH (booth:Booth {ac_id: $ac_id})
   OPTIONAL MATCH (booth)-[r]-(neighbor)
   RETURN booth AS center, r, neighbor
   LIMIT $limit
   ```
3. **Synthetic AC Node**: If booth records found:
   - Create synthetic AssemblyConstituency node with id = "AC:GKP_322"
   - Label = resolved AC ID (e.g., "GKP_322")
   - Properties include `_synthetic: True` flag
   - Connect to first N booths with HAS_BOOTH relationship
   - All booth neighbors included in edges

### Frontend Update: client_end/app/graph/page.tsx

**Improved error messaging:**
- AC queries: "No direct graph data found... Check that booths exist..."
- Other types: Original message about type filters

## Result

When user queries AC "GKP_322":
- **Before**: Empty graph (0 nodes)
- **After**: Displays booth network with synthetic AC center node
  - Central AC node (synthetic)
  - Up to 120 connected booths
  - All booth relationships (issues, candidates, parties, etc.)
  - Visual indication this is aggregated booth data

## Implementation Details

### Key Features
- **Graceful degradation**: If AC node missing, shows booth-level view
- **Synthetic node flag**: Frontend can render synthetically-created nodes differently
- **Non-destructive**: Original query path unchanged; fallback only triggers on empty results
- **Neo4j session reuse**: Uses same session for fallback query
- **Exception handling**: Maintains existing try/catch for Neo4j unavailability

### AC Node ID Resolution
- Frontend passes "GKP_322" (physical ID) or "GKP_URBAN" (logical ID)
- API aliases resolve: "GKP_URBAN" → "GKP_322"
- Booth query uses resolved physical ID

### Data Flow
```
User: AC "GKP_322" query
    ↓
Backend: Try MATCH (center:AssemblyConstituency {ac_id: "GKP_322"})
    ↓ [0 results]
Backend: Fallback to MATCH (booth:Booth {ac_id: "GKP_322"})
    ↓ [30 booths found]
Backend: Construct response with synthetic AC node + 30 booths + all edges
    ↓
Frontend: Render graph with AC center connected to booths
```

## Testing

Run local test:
```bash
python test_ac_fallback.py
```

When deployed with Neo4j configured:
1. Navigate to Knowledge Graph page
2. Select "Gorakhpur Urban AC" quick query
3. Should show AC node with booth network
4. Can still filter/navigate to individual booths

## Files Modified

- [api/queries.py](api/queries.py#L787-L913) — Added fallback logic in get_graph_subgraph
- [client_end/app/graph/page.tsx](client_end/app/graph/page.tsx#L108-L131) — Improved error messaging

## Migration/Deployment

No database migrations required. Fix applies at query layer:
- If AC nodes exist in Neo4j: Uses them (original behavior)
- If AC nodes missing: Falls back to booth network (new behavior)
- No changes to Neo4j schema or PostgreSQL
