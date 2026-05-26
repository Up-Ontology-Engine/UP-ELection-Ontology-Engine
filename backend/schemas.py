from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall health status")
    postgres: bool = Field(..., description="PostgreSQL connectivity status")
    redis: bool = Field(..., description="Redis connectivity status")
    neo4j: bool = Field(..., description="Neo4j connectivity status")
    ac: Optional[str] = Field(None, description="Test constituency identifier")

class CandidateResponse(BaseModel):
    ac_id: str
    candidates: List[Dict[str, Any]]

class SchemeResponse(BaseModel):
    ac_id: str
    schemes: List[Dict[str, Any]]

class ConversionOverviewResponse(BaseModel):
    ac_id: str
    booths: List[Dict[str, Any]]

class BoothGeoResponse(BaseModel):
    ac_id: str
    count: int
    geo: List[Dict[str, Any]]

class IntelSummaryResponse(BaseModel):
    ac_id: str
    postgres_status: str
    neo4j_status: str
    total_booths: int
    total_voters: int
    booth_details: List[Dict[str, Any]]
