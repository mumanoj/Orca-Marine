"""
Centralized Configuration for Marine Safety Thresholds.
Every threshold contains metadata (name, value, unit, category, authority, provenance, description)
to ensure ORCA operational guidelines are never misrepresented as official government regulations.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field

class ThresholdMetadata(BaseModel):
    threshold_name: str
    value: float
    unit: str
    category: Literal["ORCA_OPERATIONAL_THRESHOLD", "ORCA_DERIVED_SCORING_THRESHOLD", "VERIFIED_AUTHORITATIVE_REGULATION"]
    authority: str
    source_url: Optional[str] = None
    provenance: str
    description: str


class ORCAOperationalThresholds(BaseModel):
    """
    ORCA Internal Operational Safety Thresholds with full metadata.
    """
    wave_height_caution: ThresholdMetadata = ThresholdMetadata(
        threshold_name="small_craft_wave_height_caution",
        value=1.5,
        unit="m",
        category="ORCA_OPERATIONAL_THRESHOLD",
        authority="ORCA Operational Guidelines",
        provenance="Derived for small craft coastal navigation",
        description="Wave height limit above which small craft and fishing vessels require caution."
    )
    
    wind_speed_caution: ThresholdMetadata = ThresholdMetadata(
        threshold_name="small_craft_wind_speed_caution",
        value=30.0,
        unit="km/h",
        category="ORCA_OPERATIONAL_THRESHOLD",
        authority="ORCA Operational Guidelines",
        provenance="Derived for small craft coastal navigation",
        description="Wind speed limit above which choppy seas and wind drag require caution."
    )

    gale_wind_hazard: ThresholdMetadata = ThresholdMetadata(
        threshold_name="gale_force_wind_hazard",
        value=50.0,
        unit="km/h",
        category="ORCA_DERIVED_SCORING_THRESHOLD",
        authority="ORCA Operational Risk Engine",
        provenance="Derived gale wind risk threshold",
        description="Wind speed threshold triggering severe hazard warning in risk engine."
    )

    high_wave_hazard: ThresholdMetadata = ThresholdMetadata(
        threshold_name="high_wave_hazard",
        value=3.0,
        unit="m",
        category="ORCA_DERIVED_SCORING_THRESHOLD",
        authority="ORCA Operational Risk Engine",
        provenance="Derived high wave risk threshold",
        description="Wave height threshold triggering severe hazard warning in risk engine."
    )

    short_wave_period_caution: ThresholdMetadata = ThresholdMetadata(
        threshold_name="steep_choppy_wave_period_caution",
        value=5.0,
        unit="s",
        category="ORCA_OPERATIONAL_THRESHOLD",
        authority="ORCA Operational Guidelines",
        provenance="Hydrodynamic wave steepness guideline",
        description="Wave period below 5 seconds indicates steep choppy waves."
    )


class MarineSafetyThresholds(BaseModel):
    operational: ORCAOperationalThresholds = ORCAOperationalThresholds()


# Global Centralized Marine Thresholds Instance
MARINE_SAFETY_THRESHOLDS = MarineSafetyThresholds()
