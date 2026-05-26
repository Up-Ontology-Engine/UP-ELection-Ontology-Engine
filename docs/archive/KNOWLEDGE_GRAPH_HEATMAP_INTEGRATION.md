# Knowledge Graph ↔ Heatmap Integration

## Overview

The Knowledge Graph and Heatmap pages are now bidirectionally linked, enabling users to seamlessly navigate between connected visualizations of constituency data.

## User Workflows

### From Heatmap → Knowledge Graph

1. **Header Navigation**
   - Click the Network icon (🔗) in the heatmap header
   - Navigates to Knowledge Graph page

2. **Selected Booth → Graph Exploration**
   - Click any booth marker on the heatmap
   - If booth exists in Neo4j (`in_neo4j=true`)
   - Click "View in Knowledge Graph" button
   - Opens booth's 1-hop subgraph with all connections
   - Shows: related issues, candidates, parties, narratives

### From Knowledge Graph → Heatmap

1. **Header Navigation**
   - Click the Flame icon (🔥) in the graph page header
   - Navigates to Heatmap page

2. **Selected Booth Node → Heatmap View**
   - Select a Booth node in the graph canvas
   - Click "View on Heatmap" button in node inspector
   - Navigates to heatmap with booth marker pre-selected
   - Shows booth geolocation, voter density, pulse metrics

## Implementation Details

### Frontend Changes

#### Graph Page: `frontend/nextjs/app/graph/page.tsx`

**Header Link:**
- Added Flame icon button in header
- Navigates to `/heatmap`
- Hover state: saffron highlight

**Node Inspector Action:**
- Added "View on Heatmap" button for Booth nodes
- Link format: `/heatmap?booth={booth_id}`
- Conditionally shows only for Booth node type
- Styled with flame icon matching heatmap theme

**URL Parameter Handling:**
- Added `useSearchParams()` hook
- Detects `?type=X&id=Y` parameters from heatmap links
- Auto-loads graph for specified entity type
- Supports: `type=Booth&id=GKP_322_001`

**New Imports:**
- Added `Flame` and `MapPin` icons (lucide-react)
- Added `useSearchParams` (next/navigation)

#### Heatmap Page: `frontend/nextjs/app/heatmap/HeatMapClient.tsx`

**Header Link:**
- Added Network icon button in header
- Navigates to `/graph`
- Hover state: saffron highlight

**Selected Booth Action:**
- Added "View in Knowledge Graph" button
- Only shows if `selected.in_neo4j === true`
- Link format: `/graph?type=Booth&id={booth_id}`
- Styled with green (#10b981) to indicate graph presence
- Network icon with label

**New Imports:**
- Added `Network` icon (lucide-react)

### Data Flow

```
User clicks booth on heatmap
    ↓
HeatMapClient state: selected = {booth_id, in_neo4j, ...}
    ↓
Render "View in Knowledge Graph" button
    ↓
User clicks button → Navigate to /graph?type=Booth&id=...
    ↓
GraphPage useSearchParams effect fires
    ↓
setEntityType("Booth"), setEntityId(booth_id)
    ↓
useCallback load() function runs
    ↓
API fetches: api.subgraph("Booth", booth_id, excludeTypes)
    ↓
GraphCanvas renders booth's 1-hop connections
```

### Navigation Links

| From | To | Trigger | URL |
|------|----|---------|----|
| Heatmap | Graph | Header flame icon | `/graph` |
| Heatmap | Graph | Selected booth | `/graph?type=Booth&id={id}` |
| Graph | Heatmap | Header flame icon | `/heatmap` |
| Graph | Heatmap | Booth node selection | `/heatmap?booth={id}` |

## UI Elements

### Heatmap → Graph
```
Selected Booth Panel:
┌────────────────────┐
│ B-001              │
│ [IN GRAPH button]  │
├────────────────────┤
│ Full Intelligence  │
│ Report →           │
├────────────────────┤
│ View in Knowledge  │
│ Graph (green btn)  │
└────────────────────┘
```

### Graph → Heatmap
```
Node Inspector:
┌────────────────────┐
│ GKP_322_001        │
│ [Booth]            │
├────────────────────┤
│ Expand 1-hop       │
│ subgraph           │
├────────────────────┤
│ View on Heatmap    │
│ (orange btn)       │
└────────────────────┘
```

## Benefits

1. **Context Switching**: Users can quickly pivot between network and geographic views
2. **Exploration**: Discover booth relationships in graph, then see spatial distribution
3. **Data Validation**: Compare graph connectivity with heatmap coverage metrics
4. **Workflow Efficiency**: Single-click navigation preserves booth/entity context
5. **UI Consistency**: Matching color schemes (saffron/orange for cross-page links)

## Browser Behavior

- Links preserve existing page state (zoom, filters, selections)
- URL parameters auto-trigger graph queries
- No full page reload (Next.js client-side navigation)
- Back button returns to previous page with state preserved
- History stack works across both pages

## Testing Checklist

- [ ] Click Flame icon in graph header → lands on `/heatmap`
- [ ] Click Network icon in heatmap header → lands on `/graph`
- [ ] Select booth on heatmap, click "View in Knowledge Graph" → graph loads booth 1-hop
- [ ] Select Booth node in graph, click "View on Heatmap" → heatmap renders
- [ ] Direct link `/graph?type=Booth&id=GKP_322_001` → auto-loads booth in graph
- [ ] Browser back button navigates correctly between pages
- [ ] Link buttons only show when appropriate (Booth nodes in graph, in_neo4j booths in heatmap)

## Files Modified

- [frontend/nextjs/app/graph/page.tsx](frontend/nextjs/app/graph/page.tsx) — Header link, node inspector action, URL parameter handling
- [frontend/nextjs/app/heatmap/HeatMapClient.tsx](frontend/nextjs/app/heatmap/HeatMapClient.tsx) — Header link, selected booth action

## Future Enhancements

1. **Heatmap Booth Highlighting**: Pass booth_id to heatmap, auto-highlight on map
2. **Graph Type Filters**: Remember heatmap layer selection when switching to graph
3. **Batch Selection**: Select multiple booths on heatmap, explore collective graph
4. **Graph Overlay**: Show graph connections on heatmap as edge overlays
5. **Sync Filters**: AC selection on heatmap auto-filters graph to that AC
