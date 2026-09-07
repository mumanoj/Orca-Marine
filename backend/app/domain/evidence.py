from datetime import datetime
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    id: str = Field(description="Unique identifier for this evidence observation")
    source: str = Field(description="Originating source of the data (e.g. Open-Meteo)")
    source_url: Optional[str] = Field(default=None, description="URL endpoint of the source data")
    source_type: Literal["real_api", "local_gis", "mock_adapter", "derived_calculation"] = Field(
        description="Type of adapter/source used to retrieve the evidence"
    )
    parameter: str = Field(description="The weather/oceanographic/GIS parameter name")
    value: Any = Field(description="The measured/calculated value")
    unit: str = Field(description="Unit of measurement (e.g., m, km/h, C)")
    location: dict = Field(description="GeoJSON or coordinate dict containing latitude and longitude")
    observed_at: Optional[datetime] = Field(default=None, description="Timestamp of when observation/forecast was recorded by the source")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when ORCA retrieved this data")
    valid_from: Optional[datetime] = Field(default=None, description="Start of validation period")
    valid_until: Optional[datetime] = Field(default=None, description="End of validation period")
    status: Literal["observed", "forecast", "derived", "estimated", "unavailable"] = Field(
        description="Reliability and type status of the data observation"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    agent: str = Field(description="The agent that initiated data retrieval")
    tool: str = Field(description="The tool invoked to fetch the raw data")
