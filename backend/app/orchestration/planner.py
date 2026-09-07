import re
import json
import logging
from typing import Any, Optional, Literal
from pydantic import BaseModel, Field
from app.core.llm.manager import llm_manager

logger = logging.getLogger(__name__)

class ExecutionPlan(BaseModel):
    intent: str = Field(description="Detected user intent category")
    query_semantics: str = Field(default="NEAREST_ZONE", description="Semantic intent category for marine query reasoning (e.g. NEAREST_ZONE, HIGHEST_CHLOROPHYLL, HIGHEST_PRODUCTIVITY, SUITABLE_NEARBY_ZONES, PRODUCTIVITY_CAUSE, AVOIDANCE, ROUTING)")
    detected_language: Literal["en", "hi"] = Field(default="en", description="Language of user query: 'en' or 'hi'")
    required_agents: list[str] = Field(description="Specialized agents needed (e.g., WeatherAgent, OceanAgent, GeospatialAgent)")
    required_tools: list[str] = Field(description="Tools needed to execute the plan")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Extracted entity parameters like target date or coordinates")
    dependencies: list[str] = Field(default_factory=list, description="Task execution order/dependencies")
    geographic_requirements: dict[str, Any] = Field(default_factory=dict, description="Spatial boundaries, target coordinates, or coastal regions")
    temporal_requirements: dict[str, Any] = Field(default_factory=dict, description="Time window (e.g. today, tomorrow morning, 7-day forecast)")
    expected_evidence: list[str] = Field(default_factory=list, description="Expected marine observation types (e.g. wind_speed, wave_height)")
    reasoning_objective: str = Field(description="Target objective/goal of the query analysis")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Plan confidence score")


class PlannerAgent:
    """
    Planner Agent responsible for determining WHAT needs to be done.
    Maps a natural language query into a structured ExecutionPlan.
    Does NOT perform API/tool execution itself.
    """
    
    def __init__(self):
        self.system_instruction = (
            "You are the ORCA Planner Agent powered by Gemini. Your job is to analyze the user's marine query "
            "and decompose it into a structured execution plan. You MUST detect whether the query is in English ('en') "
            "or Hindi ('hi'). Select which specialized agents and tools are required.\n"
            "Available Agents: MarineDataDiscoveryAgent, WeatherAgent, OceanAgent, GeospatialReasoningAgent, "
            "MarineAdvisoryAgent, RouteAgent, SatelliteAgent, RiskAssessmentAgent.\n"
            "Available Tools: weather_intelligence_tool, ocean_analytics_tool, geospatial_gis_tool, "
            "marine_advisory_tool, routing_navigation_tool, satellite_eo_tool.\n\n"
            "DYNAMIC NATURAL LANGUAGE GUIDANCE:\n"
            "- Interpret ANY natural language query.\n"
            "- Extract query_semantics accurately: NEAREST_ZONE, HIGHEST_CHLOROPHYLL, HIGHEST_PRODUCTIVITY, SUITABLE_NEARBY_ZONES, PRODUCTIVITY_CAUSE, AVOIDANCE, ROUTING, WEATHER_INFO, OCEAN_STATE, HAZARD_ADVISORY, SAFETY_ASSESSMENT.\n"
            "- Weather queries: include WeatherAgent & weather_intelligence_tool.\n"
            "- Ocean state / rough sea / waves / tides / swell: include OceanAgent & ocean_analytics_tool.\n"
            "- Fishing zones / good fishing / finding fish: include SatelliteAgent, OceanAgent, pfz_advisory_tool, satellite_eo_tool.\n"
            "- Hazard / dangerous areas / avoidance: include GeospatialReasoningAgent, MarineAdvisoryAgent, geospatial_gis_tool, marine_advisory_tool.\n"
            "- General safety / can I go out: include WeatherAgent, OceanAgent, MarineAdvisoryAgent, RiskAssessmentAgent, weather_intelligence_tool, ocean_analytics_tool, marine_advisory_tool."
        )

    async def plan(
        self, 
        query: str, 
        latitude: float = 0.0, 
        longitude: float = 0.0, 
        language: str = "en",
        **kwargs: Any
    ) -> ExecutionPlan:
        """
        Generates ExecutionPlan using Gemini primary LLM (with Groq failover).
        Enriches plan with keyword-matched tools/agents to guarantee full coverage.
        """
        prompt = (
            f"User Query: '{query}'\n"
            f"Active Context Location: Latitude={latitude}, Longitude={longitude}\n"
            f"Requested Language Hint: '{language}'\n\n"
            f"Generate a validated structured execution plan. "
            f"Identify if query language is Hindi ('hi') or English ('en'). "
            f"Determine exact intent, query_semantics, required agents, tools, and reasoning objective."
        )
        try:
            plan, provider = await llm_manager.generate_structured(
                prompt=prompt,
                response_model=ExecutionPlan,
                system_instruction=self.system_instruction,
                temperature=0.1
            )
            plan.parameters["_planner_provider"] = provider
            plan.parameters["query_semantics"] = plan.query_semantics
            logger.info(f"==> [ORCA PLANNER] Plan generated via provider: {provider} | Intent: {plan.intent} | Semantics: {plan.query_semantics} | Agents: {plan.required_agents} | Tools: {plan.required_tools}")

            # Enforce Devanagari Hindi script detection if present
            if re.search(r'[\u0900-\u097F]', query) or language == "hi":
                plan.detected_language = "hi"

            # Enforce navigation agent inclusion if query asks to navigate/route
            query_l = query.lower()
            if any(w in query_l for w in ["navigate", "route", "waypoint", "heading", "take me to", "path"]):
                if "RouteAgent" not in plan.required_agents:
                    plan.required_agents.append("RouteAgent")
                if "routing_navigation_tool" not in plan.required_tools:
                    plan.required_tools.append("routing_navigation_tool")
                plan.intent = "routing_navigation"
                plan.query_semantics = "ROUTING"

            # Enforce AVOIDANCE query_semantics if query asks for restricted/avoidance zones
            if any(w in query_l for w in ["avoid", "restricted", "prohibited", "sanctuary"]):
                plan.query_semantics = "AVOIDANCE"
                plan.intent = "avoidance_geofence_analysis"
                if "GeospatialReasoningAgent" not in plan.required_agents:
                    plan.required_agents.append("GeospatialReasoningAgent")
                if "geospatial_gis_tool" not in plan.required_tools:
                    plan.required_tools.append("geospatial_gis_tool")
                if "pfz_advisory_tool" not in plan.required_tools:
                    plan.required_tools.append("pfz_advisory_tool")
                if "SatelliteAgent" not in plan.required_agents:
                    plan.required_agents.append("SatelliteAgent")

            if not plan.required_agents:
                det_plan = self._deterministic_plan(query, latitude=latitude, longitude=longitude, language=language)
                plan.required_agents = det_plan.required_agents
                plan.required_tools = det_plan.required_tools
                plan.intent = det_plan.intent
                plan.query_semantics = det_plan.query_semantics

            return plan
        except Exception as e:
            logger.warning(f"LLM planner failed: {e}. Using deterministic keyword planner.")
            return self._deterministic_plan(query, latitude=latitude, longitude=longitude, language=language)

    async def plan_mode_a_c(self, query: str, latitude: float = 0.0, longitude: float = 0.0, language: str = "en", **kwargs: Any) -> ExecutionPlan:
        return await self.plan(query, latitude, longitude, language, **kwargs)

    def plan_mode_b(self, query: str, latitude: float = 0.0, longitude: float = 0.0, language: str = "en") -> ExecutionPlan:
        return self._deterministic_plan(query, latitude, longitude, language)

    def _deterministic_plan(
        self, 
        query: str, 
        latitude: float = 0.0, 
        longitude: float = 0.0, 
        language: str = "en"
    ) -> ExecutionPlan:
        """
        Pure Python deterministic regex/rule-based planner. Bypasses LLM entirely.
        Performs explicit semantic intent classification.
        """
        query_lower = query.lower()
        
        # Detect Hindi language
        hindi_chars = re.compile(r'[\u0900-\u097F]')
        detected_lang: Literal["en", "hi"] = "hi" if (hindi_chars.search(query) or language == "hi") else "en"

        # Location Extraction
        KNOWN_LOCATIONS = {
            "kochi": (9.9312, 76.2673),
            "cochin": (9.9312, 76.2673),
            "mumbai": (19.0760, 72.8777),
            "bombay": (19.0760, 72.8777),
            "mangalore": (12.9141, 74.8560),
            "mangaluru": (12.9141, 74.8560),
            "gulf of kutch": (22.5000, 69.5000),
            "kutch": (22.5000, 69.5000),
            "goa": (15.2993, 74.1240),
            "chennai": (13.0827, 80.2707),
            "madras": (13.0827, 80.2707),
            "visakhapatnam": (17.6868, 83.2185),
            "vizag": (17.6868, 83.2185),
            "rameswaram": (9.2876, 79.3129),
            "sundarbans": (21.9497, 89.1833),
            "kanyakumari": (8.0883, 77.5385)
        }

        # Active Location Handling: Use request active coordinates as authoritative
        extracted_lat, extracted_lon = latitude, longitude
        if latitude == 0.0 and longitude == 0.0:
            extracted_lat, extracted_lon = 12.91, 74.85
            for loc_name, (lats, lons) in KNOWN_LOCATIONS.items():
                if loc_name in query_lower:
                    extracted_lat, extracted_lon = lats, lons
                    break
        else:
            # Only override if text explicitly asks for a different location ("near kochi", "at mumbai")
            for loc_name, (lats, lons) in KNOWN_LOCATIONS.items():
                if f"near {loc_name}" in query_lower or f"in {loc_name}" in query_lower or f"at {loc_name}" in query_lower:
                    extracted_lat, extracted_lon = lats, lons
                    break

        required_agents: list[str] = []
        required_tools: list[str] = []
        expected_evidence: list[str] = []
        intent = "general_status"
        query_semantics = "NEAREST_ZONE"
        reasoning_goal = "Determine query-specific marine state."
        parameters = {"extracted_location": True if (extracted_lat != latitude or extracted_lon != longitude) else False}
        dependencies: list[str] = []

        # Distance Constraint Extraction (e.g. "within 2 km", "in range of 5 km", "under 10 km", "2 km range", "within 5km")
        dist_match = re.search(r'(?:range of|within|in range of|under|less than|within range of|distance of|radius of|with in)\s*(\d+(?:\.\d+)?)\s*(?:km|kms|kilometer|kilometers|m|miles)?', query_lower)
        if not dist_match:
            dist_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:km|kms|kilometer|kilometers)\s*(?:range|radius|distance)?', query_lower)
        
        if dist_match:
            try:
                max_dist_val = float(dist_match.group(1))
                parameters["max_distance_km"] = max_dist_val
            except Exception:
                pass

        # Temporal Requirement Extraction with Specific Hour Parsing
        time_frame = "current_observation"
        is_future_forecast = False
        target_period = "present"
        target_hour = None

        hour_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', query_lower)
        if hour_match:
            hr_val = int(hour_match.group(1))
            ampm = hour_match.group(3)
            if ampm == "pm" and hr_val < 12:
                hr_val += 12
            elif ampm == "am" and hr_val == 12:
                hr_val = 0
            target_hour = hr_val

        if "tonight" in query_lower:
            is_future_forecast = True
            if target_hour is not None:
                time_frame = f"tonight_{target_hour:02d}00"
                target_period = f"Tonight at {target_hour:02d}:00 IST"
            else:
                time_frame = "tonight"
                target_period = "Tonight (22:00 - 04:00 IST)"
        elif "tomorrow morning" in query_lower or "sunrise" in query_lower:
            time_frame = "tomorrow_morning"
            is_future_forecast = True
            target_period = "Tomorrow Morning (06:00 - 12:00 IST)"
        elif "tomorrow" in query_lower:
            is_future_forecast = True
            if target_hour is not None:
                time_frame = f"tomorrow_{target_hour:02d}00"
                target_period = f"Tomorrow at {target_hour:02d}:00 IST"
            else:
                time_frame = "tomorrow"
                target_period = "Tomorrow"
        elif target_hour is not None:
            is_future_forecast = True
            time_frame = f"specific_hour_{target_hour:02d}00"
            target_period = f"Requested period at {target_hour:02d}:00 IST"
        elif any(w in query_lower for w in ["forecast", "next 6 hours", "later", "upcoming"]):
            time_frame = "forecast_24h"
            is_future_forecast = True
            target_period = "next 24 hours"

        temporal_reqs = {
            "time_frame": time_frame,
            "is_future_forecast": is_future_forecast,
            "target_period": target_period,
            "target_hour": target_hour
        }

        # ---------------------------------------------------------------------
        # EXPLICIT QUERY SEMANTICS CATEGORIZATION (Step 5E Engine)
        # ---------------------------------------------------------------------

        # A. PRODUCTIVITY CAUSE / TREND EXPLANATION
        if any(w in query_lower for w in ["why has", "why is productivity", "why has fish", "productivity declined", "productivity decrease", "productivity lower", "catch drop", "productivity changing", "why has fishing", "why are fishing conditions", "why is fishing poor"]):
            query_semantics = "PRODUCTIVITY_CAUSE"
            intent = "satellite_observation"
            required_agents = ["SatelliteAgent"]
            required_tools = ["satellite_eo_tool", "pfz_advisory_tool"]
            expected_evidence = ["sst", "chlorophyll_concentration", "official_pfz_advisory"]
            reasoning_goal = "Perform regional oceanographic causal analysis to explain marine productivity changes."

        # B. ROUTING & NAVIGATION (Priority over PFZ search if user asks to navigate/route)
        elif any(w in query_lower for w in ["route", "navigation", "navigate", "waypoint", "heading", "take me to", "how do i reach", "safest way to get there", "find a safer path", "safer path"]):
            query_semantics = "ROUTING"
            intent = "routing_navigation"
            required_agents = ["RouteAgent", "GeospatialReasoningAgent", "SatelliteAgent", "WeatherAgent", "OceanAgent"]
            required_tools = ["routing_navigation_tool", "geospatial_gis_tool", "satellite_eo_tool", "pfz_advisory_tool", "weather_intelligence_tool", "ocean_analytics_tool"]
            expected_evidence = ["route_geometry", "orca_derived_fishing_suitability"]
            reasoning_goal = "Determine candidate destination by requested semantic criterion and calculate safe transit route."

        # C. HIGHEST CHLOROPHYLL
        elif any(w in query_lower for w in ["chlorophyll", "highest chlorophyll", "chlorophyll concentration", "where is chlorophyll highest", "favourable chlorophyll", "favorable chlorophyll", "good chlorophyll", "high chlorophyll", "biologically productive", "water most biologically productive"]):
            query_semantics = "HIGHEST_CHLOROPHYLL"
            intent = "satellite_observation"
            required_agents = ["SatelliteAgent", "OceanAgent"]
            required_tools = ["satellite_eo_tool", "pfz_advisory_tool", "ocean_analytics_tool"]
            expected_evidence = ["chlorophyll_concentration", "sst", "orca_derived_fishing_suitability"]
            reasoning_goal = "Identify and rank marine areas by verified chlorophyll concentration."

        # D. HIGHEST PRODUCTIVITY / BEST FISHING ZONE
        elif any(w in query_lower for w in ["most productive", "highest productivity", "best fishing zone", "best fishing ground", "best area", "highest fishing potential", "best fishing location", "where should i fish for the best", "productive fishing", "best fishing area", "best place to fish"]):
            query_semantics = "HIGHEST_PRODUCTIVITY"
            intent = "pfz_search"
            required_agents = ["SatelliteAgent", "OceanAgent"]
            required_tools = ["pfz_advisory_tool", "satellite_eo_tool", "ocean_analytics_tool"]
            expected_evidence = ["orca_derived_fishing_suitability", "sst", "nearest_potential_fishing_zone"]
            reasoning_goal = "Rank candidate marine zones by oceanographic suitability/productivity score."

        # E. SUITABLE NEARBY ZONES (Multiple candidates / General Fishing Requests)
        elif any(w in query_lower for w in [
            "promising fishing area", "suitable fishing area", "suitable fishing zone", "where are the suitable",
            "which fishing areas are suitable", "suitable zones", "promising areas", "suitable nearby",
            "promising fishing", "promising location", "closest promising", "where can i go fishing",
            "where should i go fishing", "find me a place to fish", "find a place to fish",
            "suggest somewhere nearby", "where can i fish", "good fishing area near me", "i want to go fishing",
            "which fishing area should i choose", "where to fish"
        ]):
            query_semantics = "SUITABLE_NEARBY_ZONES"
            intent = "pfz_search"
            required_agents = ["SatelliteAgent", "OceanAgent"]
            required_tools = ["pfz_advisory_tool", "satellite_eo_tool", "ocean_analytics_tool"]
            expected_evidence = ["orca_derived_fishing_suitability", "nearest_potential_fishing_zone"]
            reasoning_goal = "Retrieve and rank multiple suitable candidate fishing zones (score >= 60/100)."

        # G. AVOIDANCE & GEOFENCING (High Priority for safety/restricted queries)
        elif any(w in query_lower for w in [
            "avoid", "avoidance", "restricted", "prohibited", "danger", "sanctuary", "dangerous areas",
            "where should i not fish", "areas should i avoid", "dangerous or restricted places", "restricted places",
            "dangerous places", "restricted zone", "restricted zones", "prohibited marine", "prohibited fishing",
            "prohibited areas", "restricted fishing"
        ]):
            query_semantics = "AVOIDANCE"
            intent = "avoidance_geofence_analysis"
            required_agents = ["GeospatialReasoningAgent", "MarineAdvisoryAgent", "SatelliteAgent"]
            required_tools = ["geospatial_gis_tool", "marine_advisory_tool", "pfz_advisory_tool"]
            expected_evidence = ["is_restricted_area", "intersecting_boundary_name", "active_warning", "nearby_restricted_zones"]
            reasoning_goal = "Identify marine protected areas, restricted geofences, and active hazard advisories to avoid."

        # F. NEAREST ZONE (Proximity Optimization)
        elif any(w in query_lower for w in [
            "nearest fishing zone", "nearest fishing location", "nearest fishing ground", "closest pfz",
            "closest fishing", "nearest potential", "closest to me", "where is the nearest", "where is nearest",
            "potential fishing zone", "potential fishing", "nearest fishing area", "closest fishing area",
            "nearest fishing", "nearest area", "closest place to fish", "where can i fish nearby",
            "fishing zone", "fishing zones", "fishing area", "fishing areas", "fishing location", "fishing locations"
        ]):
            query_semantics = "NEAREST_ZONE"
            intent = "pfz_search"
            required_agents = ["SatelliteAgent", "OceanAgent"]
            required_tools = ["pfz_advisory_tool", "satellite_eo_tool", "ocean_analytics_tool"]
            expected_evidence = ["nearest_potential_fishing_zone", "sst"]
            reasoning_goal = "Locate physically nearest Potential Fishing Zone relative to active user coordinates."

        # H. HAZARD & WARNING ADVISORIES
        elif any(w in query_lower for w in ["alert", "alerts", "warning", "warnings", "cyclone", "lightning", "advisory", "advisories", "storm", "squall"]):
            query_semantics = "HAZARD_ADVISORY"
            intent = "hazard_advisory"
            required_agents = ["MarineAdvisoryAgent", "WeatherAgent"]
            required_tools = ["marine_advisory_tool", "weather_intelligence_tool"]
            expected_evidence = ["active_warning", "temperature", "wind_speed"]
            reasoning_goal = "Identify active marine warnings, cyclone advisories, and lightning alerts."

        # I. FISHING SAFETY & DECISION SUPPORT
        elif any(w in query_lower for w in [
            "safe", "safety", "can i go", "will the weather be okay", "okay for fishing", "should i go",
            "take my boat out", "venture offshore", "venture out", "suitable for fishing", "take a boat", "is it okay",
            "good for fishing", "good to fish", "ocean currently good", "good for sailing", "good for boating",
            "fine to fish", "ok to fish", "okay to fish", "conditions for fishing", "good for"
        ]):
            query_semantics = "SAFETY_ASSESSMENT"
            intent = "safety_assessment"
            required_agents = ["WeatherAgent", "OceanAgent", "MarineAdvisoryAgent", "RiskAssessmentAgent"]
            required_tools = ["weather_intelligence_tool", "ocean_analytics_tool", "marine_advisory_tool"]
            expected_evidence = ["temperature", "wind_speed", "precipitation_probability", "wave_height", "active_warning"]
            reasoning_goal = "Evaluate combined weather, wave, marine advisory, and safety index state for vessel operation decision."

        # J. WEATHER forecast
        elif any(w in query_lower for w in ["weather", "forecast", "rain", "temperature", "temp", "wind", "outside", "what's it like"]):
            query_semantics = "WEATHER_INFO"
            intent = "weather_info"
            required_agents = ["WeatherAgent"]
            required_tools = ["weather_intelligence_tool"]
            if any(w in query_lower for w in ["wave", "waves", "swell", "sea", "rough", "ocean"]):
                required_agents.append("OceanAgent")
                required_tools.append("ocean_analytics_tool")
            expected_evidence = ["temperature", "wind_speed", "precipitation_probability"]
            reasoning_goal = "Collect real-time weather observations, wind speed, and precipitation forecast details."

        # K. OCEAN STATE & WAVES & TIDES
        elif any(w in query_lower for w in ["wave", "waves", "swell", "sea", "tide", "tides", "tidal", "high tide", "low tide", "tidal conditions", "ocean", "sea rough", "rough"]):
            query_semantics = "OCEAN_STATE"
            intent = "environmental_observation"
            required_agents = ["OceanAgent"]
            required_tools = ["ocean_analytics_tool"]
            expected_evidence = ["wave_height", "wave_period", "sea_surface_temperature"]
            reasoning_goal = "Analyze ocean wave state, wave period, and swell metrics."

        else:
            query_semantics = "NEAREST_ZONE"
            intent = "general_status"
            required_agents = ["WeatherAgent", "OceanAgent"]
            required_tools = ["weather_intelligence_tool", "ocean_analytics_tool"]
            expected_evidence = ["temperature", "wind_speed", "wave_height"]
            reasoning_goal = "Evaluate marine environmental status at active location."

        # Testing overrides
        if "force_storm" in query_lower:
            parameters["warning_active"] = True
            parameters["wave_height"] = 3.5
            if "MarineAdvisoryAgent" not in required_agents:
                required_agents.append("MarineAdvisoryAgent")
                required_tools.append("marine_advisory_tool")
            if "OceanAgent" not in required_agents:
                required_agents.append("OceanAgent")
                required_tools.append("ocean_analytics_tool")

        # Set parameter for downstream tool/adapter access
        parameters["query_semantics"] = query_semantics

        # Deduplicate
        required_agents = list(dict.fromkeys(required_agents))
        required_tools = list(dict.fromkeys(required_tools))

        return ExecutionPlan(
            intent=intent,
            query_semantics=query_semantics,
            detected_language=detected_lang,
            required_agents=required_agents,
            required_tools=required_tools,
            parameters=parameters,
            dependencies=dependencies,
            geographic_requirements={"latitude": extracted_lat, "longitude": extracted_lon},
            temporal_requirements=temporal_reqs,
            expected_evidence=expected_evidence,
            reasoning_objective=reasoning_goal,
            confidence=1.0
        )

# Global planner instance
planner_agent = PlannerAgent()
