from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class VoterStats(BaseModel):
    total: int
    total_voters: int
    male_voters: int
    female_voters: int


class IssueItem(BaseModel):
    code: str
    label: str
    count: int


class VideoItem(BaseModel):
    title: str
    url: Optional[str] = None
    channel: Optional[str] = None


class CandidateItem(BaseModel):
    name: str
    year: Optional[int] = None
    candidate_id: str
    is_incumbent: Optional[bool] = None
    is_primary_opp: Optional[bool] = None
    party: Optional[str] = None


class IntelSummaryResponse(BaseModel):
    ac_id: str
    voter_stats: VoterStats
    issues: List[IssueItem]
    youtube_count: int
    videos: List[VideoItem]
    candidates: List[CandidateItem]
