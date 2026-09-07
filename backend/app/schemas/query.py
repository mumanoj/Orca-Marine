from datetime import datetime
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field
from app.domain.evidence import Evidence

class QueryRequest(BaseModel):
    query: str = Field(description="Natural language user query")
    mode: Literal["A", "B", "C"] = Field(default="C", description="Execution Mode: A (Agentic), B (Rule-Based), C (Hybrid)")
    latitude: float = Field(description="Contextual latitude coordinates of the user/region")
    longitude: float = Field(description="Contextual longitude coordinates of the user/region")
    language: str = Field(default="en", description="Requested response language (e.g. en, hi)")
    conversation_id: Optional[str] = Field(default=None, description="Optional conversational session ID")
    reset: Optional[bool] = Field(default=False, description="Flag to reset conversation session context (New Chat)")

class MarineQueryResult(BaseModel):
    user_query: str = Field(description="Original user query input")
    conversation_id: str = Field(description="Unique conversation thread identifier")
    detected_language: str = Field(description="Language detected for generating response")
    execution_mode: Literal["A", "B", "C"] = Field(description="Mode under which query was processed")
    recommendation: str = Field(description="Final action recommendation (e.g., Proceed with caution)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall grounded confidence score")
    safety_rating: Literal["safe", "caution", "danger", "restricted", "unknown"] = Field(
        description="Categorical safety assessment"
    )
    deterministic_score: float = Field(description="Reproducible score out of 100 from the safety engine")
    explanation: str = Field(description="Detailed explanation justifying decision based on evidence")
    explainability_factors: list[dict[str, Any]] = Field(default_factory=list, description="Structured explainable AI decision factors")
    decision_summary: dict[str, Any] = Field(default_factory=dict, description="Consolidated decision factors summary")
    evidence: list[Evidence] = Field(default_factory=list, description="Traceable list of all physical observations")
    observations: dict[str, Any] = Field(default_factory=dict, description="Consolidated metrics/weather/ocean status summary")
    sources: list[str] = Field(default_factory=list, description="Unique data sources cited")
    timestamps: dict[str, datetime] = Field(default_factory=dict, description="Tracking timestamps for events")
    warnings: list[str] = Field(default_factory=list, description="Warnings (boundaries, cyclone, severe wave height, etc.)")
    map_markers: list[dict[str, Any]] = Field(default_factory=list, description="Map pins containing locations and hazard levels")
    map_layers: list[dict[str, Any]] = Field(default_factory=list, description="Layers such as restricted boundary polygons")
    geographic_coordinates: dict[str, float] = Field(description="Query reference latitude and longitude")
    route_information: Optional[dict[str, Any]] = Field(default=None, description="Navigation route coordinates and travel times")
    geofence_information: Optional[dict[str, Any]] = Field(default=None, description="Status of geofenced regions intersected")
    agents_executed: list[str] = Field(default_factory=list, description="List of logical agents executed")
    tools_executed: list[str] = Field(default_factory=list, description="List of tools invoked")
    execution_duration: float = Field(description="API request execution latency in seconds")
    persisted: bool = Field(default=False, description="Whether query outcome was successfully stored in MongoDB")
    errors: list[str] = Field(default_factory=list, description="Log of failures or degraded-state reports")
