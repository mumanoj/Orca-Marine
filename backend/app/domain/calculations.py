import math
from typing import Any, Optional, Literal
from pydantic import BaseModel, Field
from app.domain.evidence import Evidence
from app.domain.thresholds import MARINE_SAFETY_THRESHOLDS, MarineSafetyThresholds

class SafetyEvaluation(BaseModel):
    score: float
    rating: Literal["safe", "caution", "danger", "restricted", "unknown"]
    warnings: list[str]
    penalties: dict[str, float]
    factors: dict[str, Any]
    triggered_factors: list[str] = Field(default_factory=list)
    violated_thresholds: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class FishingSuitabilityEvaluation(BaseModel):
    suitability_score: float
    category: Literal["high", "moderate", "low", "unsuitable"]
    contributing_parameters: dict[str, Any]
    evidence_ids: list[str]
    is_official_pfz: bool = False
    provenance_disclaimer: str = (
        "NOTE: This score represents an ORCA-DERIVED FISHING SUITABILITY ESTIMATE calculated "
        "from SST, sea state, and wind conditions. It is NOT an official INCOIS PFZ advisory."
    )


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> dict[str, float]:
    """
    Calculates exact great-circle distance between two geographic points using Haversine formula.
    Returns distance in nautical miles (NM) and kilometers (km).
    """
    R_km = 6371.0  # Earth's radius in kilometers
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    distance_km = R_km * c
    distance_nm = distance_km / 1.852  # 1 NM = 1.852 km
    
    return {
        "km": round(distance_km, 3),
        "nautical_miles": round(distance_nm, 3)
    }


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates initial compass bearing (azimuth) from point 1 to point 2 in degrees (0-360°).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    
    bearing_deg = math.degrees(math.atan2(y, x))
    return round((bearing_deg + 360.0) % 360.0, 2)


def calculate_eta(distance_km: float, speed_knots: float) -> float:
    """
    Calculates estimated time of arrival / transit duration in hours.
    """
    if speed_knots <= 0.0:
        return float('inf')
    speed_kmh = speed_knots * 1.852
    return round(distance_km / speed_kmh, 2)


def calculate_fishing_suitability(
    sst: Optional[float] = None,
    wave_height: Optional[float] = None,
    wind_speed: Optional[float] = None,
    chlorophyll: Optional[float] = None,
    evidence_ids: Optional[list[str]] = None
) -> FishingSuitabilityEvaluation:
    """
    Deterministic Fishing Suitability Calculation Engine.
    Evaluates environmental parameters (SST, sea state, wind) to derive fishing suitability.
    IMPORTANT: Explicitly labelled as ORCA-DERIVED ESTIMATE, distinct from official INCOIS PFZ.
    """
    score = 100.0
    contributing: dict[str, Any] = {}
    ev_ids = evidence_ids or []

    # 1. SST Evaluation (Optimal 27.0 - 29.5 °C for Indian pelagic fisheries)
    if sst is not None:
        contributing["sst"] = sst
        if 27.0 <= sst <= 29.5:
            contributing["sst_status"] = "optimal"
        elif 25.0 <= sst < 27.0 or 29.5 < sst <= 31.0:
            score -= 15.0
            contributing["sst_status"] = "sub_optimal"
        else:
            score -= 35.0
            contributing["sst_status"] = "unfavorable"

    # 2. Sea State / Wave Height Evaluation
    if wave_height is not None:
        contributing["wave_height"] = wave_height
        if wave_height >= 2.5:
            score = 0.0  # Hazardous sea state rendering fishing unsafe
            contributing["sea_state"] = "hazardous"
        elif wave_height >= 1.8:
            score -= 30.0
            contributing["sea_state"] = "rough"
        else:
            contributing["sea_state"] = "favorable"

    # 3. Wind Speed Evaluation
    if wind_speed is not None:
        contributing["wind_speed"] = wind_speed
        if wind_speed >= 40.0:
            score = 0.0
            contributing["wind_condition"] = "gale_force"
        elif wind_speed >= 30.0:
            score -= 25.0
            contributing["wind_condition"] = "strong_wind"

    # 4. Chlorophyll Bonus (if present)
    if chlorophyll is not None and isinstance(chlorophyll, (int, float)) and chlorophyll > 0.5:
        score += 10.0
        contributing["chlorophyll"] = chlorophyll
        contributing["chlorophyll_status"] = "high_productivity"

    score = max(0.0, min(100.0, score))

    if score >= 75.0:
        category = "high"
    elif score >= 50.0:
        category = "moderate"
    elif score >= 25.0:
        category = "low"
    else:
        category = "unsuitable"

    return FishingSuitabilityEvaluation(
        suitability_score=round(score, 1),
        category=category,
        contributing_parameters=contributing,
        evidence_ids=ev_ids,
        is_official_pfz=False
    )


def evaluate_safety(
    evidence_list: list[Evidence], 
    thresholds: MarineSafetyThresholds = MARINE_SAFETY_THRESHOLDS
) -> SafetyEvaluation:
    """
    Deterministic Safety & Risk Calculation Engine.
    Exclusively evaluates safety variables without LLM interaction using centralized thresholds.
    Same inputs -> Same output.
    """
    score = 100.0
    warnings = []
    penalties = {}
    factors = {}
    triggered_factors = []
    violated_thresholds = []
    evidence_ids = []

    # Extract relevant parameters from evidence
    wind_speed = None
    wave_height = None
    wave_period = None
    is_restricted = False
    active_warning = False
    warning_details = ""
    boundary_name = "None"

    for ev in evidence_list:
        evidence_ids.append(ev.id)
        if ev.parameter == "wind_speed":
            wind_speed = float(ev.value) if isinstance(ev.value, (int, float)) else None
            if wind_speed is not None:
                factors["wind_speed"] = {"value": wind_speed, "unit": ev.unit}
        elif ev.parameter in ["wave_height", "forecast_wave_height"]:
            wave_height = float(ev.value) if isinstance(ev.value, (int, float)) else None
            if wave_height is not None:
                factors["wave_height"] = {"value": wave_height, "unit": ev.unit}
        elif ev.parameter == "wave_period":
            wave_period = float(ev.value) if isinstance(ev.value, (int, float)) else None
            if wave_period is not None:
                factors["wave_period"] = {"value": wave_period, "unit": ev.unit}
        elif ev.parameter == "is_restricted_area":
            is_restricted = bool(ev.value)
            factors["is_restricted_area"] = is_restricted
        elif ev.parameter == "intersecting_boundary_name":
            boundary_name = str(ev.value)
            factors["boundary_name"] = boundary_name
        elif ev.parameter == "active_warning":
            active_warning = bool(ev.value)
            factors["active_warning"] = active_warning
        elif ev.parameter == "warning_details":
            warning_details = str(ev.value)

    oper = thresholds.operational

    # 1. Restricted / Protected Area check (takes ultimate precedence)
    if is_restricted:
        penalties["geofence_violation"] = 100.0
        score = 0.0
        triggered_factors.append("geofence_prohibition")
        violated_thresholds.append("RESTRICTED_MARINE_GEONODE")
        warnings.append(f"RESTRICTED AREA: Selected coordinate lies inside geofenced marine zone '{boundary_name}'.")

    # If not restricted, compute cumulative meteorological penalties
    else:
        # 2. Cyclone / severe storm advisories
        if active_warning:
            penalties["active_advisory"] = 80.0
            score -= 80.0
            triggered_factors.append("active_cyclone_advisory")
            violated_thresholds.append("SEVERE_STORM_ADVISORY")
            warnings.append(f"METEOROLOGICAL WARNING: {warning_details or 'Active marine storm warning detected.'}")

        # 3. Wind speed checks
        if wind_speed is not None:
            if wind_speed >= oper.gale_wind_hazard.value:
                penalties["gale_winds"] = 50.0
                score -= 50.0
                triggered_factors.append("gale_wind")
                violated_thresholds.append(f"ORCA_GALE_WIND_HAZARD ({oper.gale_wind_hazard.value} km/h)")
                warnings.append(f"DANGEROUS WIND: Gale force winds detected ({wind_speed} km/h >= {oper.gale_wind_hazard.value} km/h).")
            elif wind_speed >= oper.wind_speed_caution.value:
                penalties["high_winds"] = 25.0
                score -= 25.0
                triggered_factors.append("high_wind")
                violated_thresholds.append(f"ORCA_SMALL_CRAFT_WIND_CAUTION ({oper.wind_speed_caution.value} km/h)")
                warnings.append(f"HIGH WIND: Strong winds ({wind_speed} km/h). Caution advised.")

        # 4. Wave height checks
        if wave_height is not None:
            if wave_height >= oper.high_wave_hazard.value:
                penalties["dangerous_waves"] = 60.0
                score -= 60.0
                triggered_factors.append("high_wave_alert")
                violated_thresholds.append(f"ORCA_HIGH_WAVE_HAZARD ({oper.high_wave_hazard.value} m)")
                warnings.append(f"DANGEROUS WAVES: Sea state is severe (wave height {wave_height} m >= {oper.high_wave_hazard.value} m).")
            elif wave_height >= oper.wave_height_caution.value:
                penalties["high_waves"] = 20.0
                score -= 20.0
                triggered_factors.append("choppy_waves")
                violated_thresholds.append(f"ORCA_SMALL_CRAFT_WAVE_CAUTION ({oper.wave_height_caution.value} m)")
                warnings.append(f"HIGH WAVES: Moderate to high waves ({wave_height} m).")

        # 5. Short wave period choppy sea check
        if wave_period is not None and wave_period < oper.short_wave_period_caution.value:
            penalties["short_period_waves"] = 15.0
            score -= 15.0
            triggered_factors.append("steep_short_period_waves")
            violated_thresholds.append(f"ORCA_WAVE_PERIOD_CAUTION ({oper.short_wave_period_caution.value} s)")
            warnings.append(f"CHOPPY SEAS: Short wave period ({wave_period} s) indicates steep choppy seas.")

        # 6. Missing data / feed unavailability uncertainty penalty
        unavail_items = [e for e in evidence_list if e.status == "unavailable"]
        if unavail_items or (wind_speed is None and wave_height is None):
            penalty_amount = min(40.0, 15.0 * max(1, len(unavail_items)))
            penalties["missing_data_uncertainty"] = penalty_amount
            score -= penalty_amount
            triggered_factors.append("missing_feed_uncertainty")
            warnings.append(f"UNCERTAINTY NOTICE: {len(unavail_items) if unavail_items else 'Key'} data feed(s) currently unavailable. Safety score adjusted for missing observation coverage.")

    # Bound the score
    score = max(0.0, min(100.0, score))

    # Determine Safety Rating
    if is_restricted:
        rating = "restricted"
    elif active_warning or score <= 30.0:
        rating = "danger"
    elif score <= 70.0:
        rating = "caution"
    else:
        rating = "safe"

    return SafetyEvaluation(
        score=score,
        rating=rating,
        warnings=warnings,
        penalties=penalties,
        factors=factors,
        triggered_factors=triggered_factors,
        violated_thresholds=violated_thresholds,
        evidence_ids=evidence_ids
    )
