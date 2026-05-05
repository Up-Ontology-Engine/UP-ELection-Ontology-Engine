"""
Pydantic schemas for the NLP extraction pipeline.
These are the source of truth — both LLM (via Instructor) and rule-based
classifier output must conform to ExtractionResult.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from enum import Enum


class EntityType(str, Enum):
    PARTY     = "party"
    CANDIDATE = "candidate"
    SCHEME    = "scheme"
    ISSUE     = "issue"
    GOVT      = "govt"


class IssueType(str, Enum):
    WATER        = "water"
    ROADS        = "roads"
    ELECTRICITY  = "electricity"
    JOBS         = "jobs"
    WOMEN_SAFETY = "women_safety"
    PRICE_RISE   = "price_rise"
    FARMER       = "farmer"
    SUGARCANE    = "sugarcane"
    HEALTH       = "health"
    EDUCATION    = "education"
    CORRUPTION   = "corruption"
    LAW_ORDER    = "law_order"
    OTHER        = "other"


ENTITY_NORMALISATION = {
    "भाजपा": "BJP", "bjp": "BJP", "कमल": "BJP", "lotus": "BJP",
    "double engine": "BJP", "डबल इंजन": "BJP",
    "yogi": "Yogi Adityanath", "योगी": "Yogi Adityanath",
    "modi": "Narendra Modi", "मोदी": "Narendra Modi",
    "समाजवादी": "SP", "सपा": "SP", "cycle": "SP", "साइकिल": "SP",
    "akhilesh": "Akhilesh Yadav", "अखिलेश": "Akhilesh Yadav",
    "netaji": "Akhilesh Yadav", "नेताजी": "Akhilesh Yadav",
    "बसपा": "BSP", "हाथी": "BSP", "elephant": "BSP",
    "mayawati": "Mayawati", "मायावती": "Mayawati", "behan ji": "Mayawati",
    "कांग्रेस": "Congress", "inc": "Congress",
    "rahul": "Rahul Gandhi", "राहुल": "Rahul Gandhi",
}


class SentimentStatement(BaseModel):
    entity: str = Field(
        ...,
        description="Political entity: party name, candidate name, or govt reference"
    )
    entity_type: EntityType
    issue: Optional[IssueType] = Field(
        None,
        description="Issue this sentiment is about. Null if purely about a party/candidate."
    )
    polarity: Literal[-1, 0, 1] = Field(
        ...,
        description="-1=negative/criticism, 0=neutral/factual, 1=positive/praise"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    location_mention: Optional[str] = Field(
        None,
        description="Raw location text if any geographic reference found"
    )
    language: str = Field(..., description="hi | bho | en | mix")
    evidence: str = Field(
        ...,
        description="1–4 word phrase from original text justifying the polarity"
    )

    @field_validator("entity", mode="before")
    @classmethod
    def normalise_entity(cls, v: str) -> str:
        return ENTITY_NORMALISATION.get(v.lower().strip(), v.strip())


class ExtractionResult(BaseModel):
    statements: List[SentimentStatement] = Field(default_factory=list)
    primary_language: str = Field("hi")
    contains_bhojpuri: bool = False
    is_political: bool = True


class GeoResolution(BaseModel):
    matched_text: Optional[str]
    mapped_id: str
    mapped_type: str           # "booth" | "ac"
    mapped_booth_id: Optional[str]
    mapped_ac_id: str
    geo_confidence: float


class PipelineResult(BaseModel):
    """Full output of the NLP pipeline for one text unit."""
    source_id: str
    source_type: str
    text_raw: str
    text_normalized_hi: Optional[str] = None
    language_detected: str = "unknown"
    translation_method: str = "none"    # bhashini | indictrans2 | none
    extraction: ExtractionResult
    extraction_method: str              # llm | rule_based | llm+rule_fallback
    geo_resolution: Optional[GeoResolution] = None
    final_polarity: Optional[int] = None
    final_issue: Optional[str] = None
    final_entity: Optional[str] = None
    final_confidence: float = 0.0
    processing_errors: List[str] = Field(default_factory=list)
