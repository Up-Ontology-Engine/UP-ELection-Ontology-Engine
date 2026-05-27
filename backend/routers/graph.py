from __future__ import annotations

from fastapi import APIRouter, Query

from ..queries import get_graph_subgraph, get_infrastructure_overview, get_ontology_status
from ..validation import InputValidationRoute

router = APIRouter(route_class=InputValidationRoute)


@router.get("/graph/subgraph")
def graph_subgraph(
    entity_type: str = Query(..., description="AC | Booth | Issue | Candidate | Party | Scheme"),
    entity_id: str = Query(..., description="The entity's primary ID value"),
    exclude_types: list[str] = Query(default=[], description="Node types to exclude from results"),
    limit: int = Query(default=120, ge=1, le=300, description="Max neighbor nodes to return"),
):
    """1-hop subgraph from Neo4j around the specified entity."""
    return get_graph_subgraph(entity_type, entity_id, exclude_types=exclude_types, limit=limit)


@router.get("/infrastructure/overview")
def infrastructure_overview():
    """PostgreSQL table row counts + Neo4j node/edge topology for the Data Infrastructure page."""
    return get_infrastructure_overview()


@router.get("/ontology/status")
def ontology_status():
    """Live graph topology — node/rel counts, active constraints, PG table stats. Powers the Ontology Layer page."""
    return get_ontology_status()
