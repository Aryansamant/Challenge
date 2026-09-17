from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


Severity = Literal["critical", "poor", "moderate", "adequate", "unknown"]
Horizon = Literal["short", "medium", "long"]
Confidence = Literal["low", "moderate", "high"]


class SoilHealth(BaseModel):
    organic_carbon_pct: Optional[float] = Field(default=None, ge=0, le=20)
    ph: Optional[float] = Field(default=None, ge=0, le=14)
    moisture: Optional[str] = None
    texture: Optional[str] = None
    erosion: Optional[str] = None


class Climate(BaseModel):
    rainfall: Optional[str] = None
    rainfall_mm: Optional[float] = None
    temperature: Optional[str] = None
    mean_temp_c: Optional[float] = None
    drought_risk: Optional[str] = None
    climate_zone: Optional[str] = None


class LandUse(BaseModel):
    type: Optional[str] = None
    crop: Optional[str] = None
    management: Optional[str] = None
    tillage: Optional[str] = None
    irrigation: Optional[str] = None
    livestock: Optional[str] = None


class BiodiversityIndicators(BaseModel):
    species_richness: Optional[str] = None
    habitat_diversity: Optional[str] = None
    native_cover_pct: Optional[float] = None
    pollinator_status: Optional[str] = None


class HumanImpact(BaseModel):
    pollution: Optional[str] = None
    deforestation: Optional[str] = None
    fragmentation: Optional[str] = None
    pesticide_intensity: Optional[str] = None
    grazing_pressure: Optional[str] = None


class GeoContext(BaseModel):
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    region: Optional[str] = None
    elevation_m: Optional[float] = None


class LandProfile(BaseModel):
    soil: SoilHealth = Field(default_factory=SoilHealth)
    climate: Climate = Field(default_factory=Climate)
    land_use: LandUse = Field(default_factory=LandUse)
    biodiversity: BiodiversityIndicators = Field(default_factory=BiodiversityIndicators)
    human_impact: HumanImpact = Field(default_factory=HumanImpact)
    geo: GeoContext = Field(default_factory=GeoContext)
    notes: list[str] = Field(default_factory=list)

    def filled_variable_count(self) -> int:
        blobs = [
            self.soil.model_dump(exclude_none=True),
            self.climate.model_dump(exclude_none=True),
            self.land_use.model_dump(exclude_none=True),
            self.biodiversity.model_dump(exclude_none=True),
            self.human_impact.model_dump(exclude_none=True),
            self.geo.model_dump(exclude_none=True),
        ]
        return sum(len(b) for b in blobs)

    def as_context_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class Evidence(BaseModel):
    source: str
    year: Optional[int] = None
    citation: str
    snippet: str
    relevance: float = 0.0
    doc_id: str = ""


class ImpactedMetric(BaseModel):
    metric: str
    direction: Literal["increase", "decrease", "stabilize"]
    expected_change: str
    mechanism: str


class Recommendation(BaseModel):
    title: str
    action: str
    why_it_works: str
    impacted_metrics: list[ImpactedMetric]
    time_horizon: Horizon
    confidence: Confidence
    evidence: list[Evidence]
    synergies: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    addresses_limiting_factors: list[str] = Field(default_factory=list)


class MetricStatus(BaseModel):
    metric: str
    value: Optional[str] = None
    severity: Severity
    rationale: str
    linked_metrics: list[str] = Field(default_factory=list)


class FollowUpQuestion(BaseModel):
    slot: str
    question: str
    why_needed: str


class CausalChain(BaseModel):
    path: list[str]
    explanation: str


class RecommendationPack(BaseModel):
    diagnosis_summary: str
    limiting_factors: list[str]
    metric_status: list[MetricStatus]
    causal_chains: list[CausalChain]
    recommendations: list[Recommendation]
    follow_ups: list[FollowUpQuestion] = Field(default_factory=list)
    retrieved_evidence: list[Evidence] = Field(default_factory=list)
    confidence_overall: Confidence = "moderate"
    variables_used: list[str] = Field(default_factory=list)
    retrieval_notes: str = ""


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: Optional[str] = None
    profile: Optional[LandProfile] = None
    coordinates: Optional[list[float]] = None


class ChatResponse(BaseModel):
    session_id: str
    assistant_message: str
    pack: Optional[RecommendationPack] = None
    profile: LandProfile
    needs_more_input: bool = False
    retrieved_doc_ids: list[str] = Field(default_factory=list)
