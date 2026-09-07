from datetime import datetime
from typing import Any
from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.tools.registry import BaseTool
from app.domain.evidence import Evidence
from app.domain.calculations import evaluate_safety

class MarineDataDiscoveryAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "MarineDataDiscoveryAgent"

    @property
    def description(self) -> str:
        return "Discovers relevant marine datasets, spatial layers, and tool adapters for coordinate bounds."

    @property
    def required_tools(self) -> list[str]:
        return [
            "weather_intelligence_tool",
            "ocean_analytics_tool",
            "geospatial_gis_tool",
            "marine_advisory_tool",
            "routing_navigation_tool",
            "satellite_eo_tool",
            "pfz_advisory_tool"
        ]

    async def execute(self, input_data: AgentInput, tools: dict[str, BaseTool], **kwargs: Any) -> AgentOutput:
        messages = [f"{self.name} activated. Discovery target: ({input_data.latitude}, {input_data.longitude})."]
        now = datetime.utcnow()
        
        # Discovers applicable tools from registry
        all_available_tools = list(tools.keys())
        query_str = input_data.context.get("raw_query", "").lower()
        
        selected_adapters = []
        if "pfz" in query_str or "fishing" in query_str or "suitability" in query_str or "fish" in query_str:
            if "pfz_advisory_tool" in tools:
                selected_adapters.append("pfz_advisory_tool")
            if "satellite_eo_tool" in tools and "satellite_eo_tool" not in selected_adapters:
                selected_adapters.append("satellite_eo_tool")
        if "sst" in query_str or "temperature" in query_str or "chlorophyll" in query_str or "satellite" in query_str:
            if "satellite_eo_tool" in tools and "satellite_eo_tool" not in selected_adapters:
                selected_adapters.append("satellite_eo_tool")
        if "wave" in query_str or "swell" in query_str or "tide" in query_str or "current" in query_str or "sea" in query_str:
            if "ocean_analytics_tool" in tools:
                selected_adapters.append("ocean_analytics_tool")
        if any(w in query_str for w in ["alert", "cyclone", "warning", "lightning", "advisory", "hazard"]):
            if "marine_advisory_tool" in tools and "marine_advisory_tool" not in selected_adapters:
                selected_adapters.append("marine_advisory_tool")
        if "weather" in query_str or "wind" in query_str or "rain" in query_str or "weather" in query_str:
            if "weather_intelligence_tool" in tools and "weather_intelligence_tool" not in selected_adapters:
                selected_adapters.append("weather_intelligence_tool")

        if not selected_adapters:
            selected_adapters = all_available_tools

        messages.append(f"Discovered {len(all_available_tools)} total tools; selected {len(selected_adapters)} relevant adapters for query scope.")

        evidence = [
            Evidence(
                id=f"disc_{int(now.timestamp())}",
                source="ORCA Discovery Index",
                source_type="derived_calculation",
                parameter="discovered_tool_adapters",
                value={"total_count": len(all_available_tools), "selected_adapters": selected_adapters},
                unit="count",
                location={"lat": input_data.latitude, "lon": input_data.longitude},
                retrieved_at=now,
                status="derived",
                confidence=1.0,
                agent=self.name,
                tool="discovery_registry"
            )
        ]
        
        return AgentOutput(
            agent_name=self.name,
            status="completed",
            evidence=evidence,
            messages=messages
        )


class WeatherAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "WeatherAgent"

    @property
    def description(self) -> str:
        return "Collects and interprets weather parameters (temp, wind, rain) for the region."

    @property
    def required_tools(self) -> list[str]:
        return ["weather_intelligence_tool"]

    async def execute(self, input_data: AgentInput, tools: dict[str, BaseTool], **kwargs: Any) -> AgentOutput:
        tool_name = "weather_intelligence_tool"
        messages = [f"{self.name} activated. Objective: Collect weather variables."]
        
        if tool_name not in tools:
            err = f"Required tool '{tool_name}' not available."
            return AgentOutput(agent_name=self.name, status="failed", errors=[err], messages=messages)

        try:
            tool = tools[tool_name]
            messages.append(f"Invoking tool adapter: {tool_name}")
            tool_kwargs = {
                "latitude": input_data.latitude,
                "longitude": input_data.longitude,
                "agent_name": self.name
            }
            if "temporal_requirements" in input_data.context:
                tool_kwargs["temporal_requirements"] = input_data.context["temporal_requirements"]
            if "raw_query" in input_data.context:
                tool_kwargs["raw_query"] = input_data.context["raw_query"]
            if "query_semantics" in input_data.context:
                tool_kwargs["query_semantics"] = input_data.context["query_semantics"]

            evidence = await tool.execute(**tool_kwargs)
            messages.append(f"Retrieved {len(evidence)} weather observation parameters.")
            return AgentOutput(
                agent_name=self.name,
                status="completed",
                evidence=evidence,
                messages=messages
            )
        except Exception as e:
            err_msg = f"Weather tool failure: {str(e)}"
            messages.append(f"Execution failed: {err_msg}")
            return AgentOutput(agent_name=self.name, status="failed", errors=[err_msg], messages=messages)


class OceanAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "OceanAgent"

    @property
    def description(self) -> str:
        return "Analyzes wave height, wave period, and ocean swell conditions."

    @property
    def required_tools(self) -> list[str]:
        return ["ocean_analytics_tool"]

    async def execute(self, input_data: AgentInput, tools: dict[str, BaseTool], **kwargs: Any) -> AgentOutput:
        tool_name = "ocean_analytics_tool"
        messages = [f"{self.name} activated. Objective: Analyze wave characteristics."]
        
        if tool_name not in tools:
            err = f"Required tool '{tool_name}' not available."
            return AgentOutput(agent_name=self.name, status="failed", errors=[err], messages=messages)

        try:
            tool = tools[tool_name]
            wave_height = input_data.context.get("wave_height", 1.2)
            tool_kwargs = {
                "latitude": input_data.latitude,
                "longitude": input_data.longitude,
                "agent_name": self.name,
                "wave_height": wave_height
            }
            if "temporal_requirements" in input_data.context:
                tool_kwargs["temporal_requirements"] = input_data.context["temporal_requirements"]
            if "raw_query" in input_data.context:
                tool_kwargs["raw_query"] = input_data.context["raw_query"]
            if "query_semantics" in input_data.context:
                tool_kwargs["query_semantics"] = input_data.context["query_semantics"]

            evidence = await tool.execute(**tool_kwargs)
            messages.append("Oceanographic wave measurements collected successfully.")
            return AgentOutput(
                agent_name=self.name,
                status="completed",
                evidence=evidence,
                messages=messages
            )
        except Exception as e:
            err_msg = f"Ocean tool failure: {str(e)}"
            messages.append(f"Execution failed: {err_msg}")
            return AgentOutput(agent_name=self.name, status="failed", errors=[err_msg], messages=messages)


class GeospatialReasoningAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "GeospatialReasoningAgent"

    @property
    def description(self) -> str:
        return "Performs GIS point-in-polygon checks against protected marine areas and restricted geofences."

    @property
    def required_tools(self) -> list[str]:
        return ["geospatial_gis_tool"]

    async def execute(self, input_data: AgentInput, tools: dict[str, BaseTool], **kwargs: Any) -> AgentOutput:
        tool_name = "geospatial_gis_tool"
        messages = [f"{self.name} activated. Target coordinate: ({input_data.latitude}, {input_data.longitude})."]
        
        if tool_name not in tools:
            err = f"Required tool '{tool_name}' not available."
            return AgentOutput(agent_name=self.name, status="failed", errors=[err], messages=messages)

        try:
            tool = tools[tool_name]
            evidence = await tool.execute(
                latitude=input_data.latitude, 
                longitude=input_data.longitude,
                agent_name=self.name
            )
            messages.append("Spatial boundary and geofence intersection checks completed.")
            return AgentOutput(
                agent_name=self.name,
                status="completed",
                evidence=evidence,
                messages=messages
            )
        except Exception as e:
            err_msg = f"GIS reasoning error: {str(e)}"
            return AgentOutput(agent_name=self.name, status="failed", errors=[err_msg], messages=messages)


class RiskAssessmentAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "RiskAssessmentAgent"

    @property
    def description(self) -> str:
        return "Evaluates accumulated evidence against deterministic domain risk math formulas."

    @property
    def required_tools(self) -> list[str]:
        return []

    async def execute(self, input_data: AgentInput, tools: dict[str, BaseTool], **kwargs: Any) -> AgentOutput:
        messages = [f"{self.name} activated. Evaluating domain risk matrix."]
        accumulated_evidence: list[Evidence] = kwargs.get("evidence", [])
        now = datetime.utcnow()
        
        safety_eval = evaluate_safety(accumulated_evidence)
        messages.append(f"Deterministic risk evaluation score: {safety_eval.score}/100. Rating: {safety_eval.rating}.")

        evidence = [
            Evidence(
                id=f"risk_{int(now.timestamp())}",
                source="ORCA Risk Assessment Engine",
                source_type="derived_calculation",
                parameter="calculated_safety_rating",
                value={"score": safety_eval.score, "rating": safety_eval.rating, "penalties": safety_eval.penalties},
                unit="rating",
                location={"lat": input_data.latitude, "lon": input_data.longitude},
                retrieved_at=now,
                status="derived",
                confidence=1.0,
                agent=self.name,
                tool="evaluate_safety"
            )
        ]

        return AgentOutput(
            agent_name=self.name,
            status="completed",
            evidence=evidence,
            messages=messages
        )


class MarineAdvisoryAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "MarineAdvisoryAgent"

    @property
    def description(self) -> str:
        return "Checks active cyclone, storm, and lightning warnings."

    @property
    def required_tools(self) -> list[str]:
        return ["marine_advisory_tool"]

    async def execute(self, input_data: AgentInput, tools: dict[str, BaseTool], **kwargs: Any) -> AgentOutput:
        tool_name = "marine_advisory_tool"
        messages = [f"{self.name} activated. Objective: Check storm and severe weather advisories."]
        
        if tool_name not in tools:
            err = f"Required tool '{tool_name}' not available."
            return AgentOutput(agent_name=self.name, status="failed", errors=[err], messages=messages)

        try:
            tool = tools[tool_name]
            warning_active = input_data.context.get("warning_active", False)
            evidence = await tool.execute(
                latitude=input_data.latitude, 
                longitude=input_data.longitude,
                agent_name=self.name,
                warning_active=warning_active
            )
            messages.append("Storm and advisory checks complete.")
            return AgentOutput(
                agent_name=self.name,
                status="completed",
                evidence=evidence,
                messages=messages
            )
        except Exception as e:
            err_msg = f"Advisory tool error: {str(e)}"
            return AgentOutput(agent_name=self.name, status="failed", errors=[err_msg], messages=messages)


class RouteAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "RouteAgent"

    @property
    def description(self) -> str:
        return "Calculates optimal navigation routes, travel distance, and ETA metrics."

    @property
    def required_tools(self) -> list[str]:
        return ["routing_navigation_tool"]

    async def execute(self, input_data: AgentInput, tools: dict[str, BaseTool], **kwargs: Any) -> AgentOutput:
        tool_name = "routing_navigation_tool"
        messages = [f"{self.name} activated. Objective: Compute navigation geometry."]
        
        if tool_name not in tools:
            err = f"Required tool '{tool_name}' not available."
            return AgentOutput(agent_name=self.name, status="failed", errors=[err], messages=messages)

        try:
            tool = tools[tool_name]
            
            # Destination selection: context dest -> target PFZ in evidence -> dynamic offshore candidate
            dest_lat = input_data.context.get("dest_lat")
            dest_lon = input_data.context.get("dest_lon")

            if dest_lat is None or dest_lon is None:
                accumulated_evidence = kwargs.get("evidence", [])
                pfz_ev = next((e for e in accumulated_evidence if e.parameter == "nearest_potential_fishing_zone"), None)
                if pfz_ev and isinstance(pfz_ev.value, dict) and "latitude" in pfz_ev.value:
                    dest_lat = pfz_ev.value["latitude"]
                    dest_lon = pfz_ev.value["longitude"]
                else:
                    from app.domain.marine_geospatial import generate_dynamic_offshore_candidates
                    offshore_cands = generate_dynamic_offshore_candidates(input_data.latitude, input_data.longitude)
                    dest_lat = offshore_cands[0]["lat"]
                    dest_lon = offshore_cands[0]["lon"]

            evidence = await tool.execute(
                latitude=input_data.latitude, 
                longitude=input_data.longitude,
                agent_name=self.name,
                dest_lat=dest_lat,
                dest_lon=dest_lon
            )
            messages.append(f"Navigation transit route calculated to offshore destination ({dest_lat}, {dest_lon}).")
            return AgentOutput(
                agent_name=self.name,
                status="completed",
                evidence=evidence,
                messages=messages
            )
        except Exception as e:
            err_msg = f"Routing tool error: {str(e)}"
            return AgentOutput(agent_name=self.name, status="failed", errors=[err_msg], messages=messages)


class SatelliteAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "SatelliteAgent"

    @property
    def description(self) -> str:
        return "Retrieves satellite Earth Observation datasets (SST and Chlorophyll)."

    @property
    def required_tools(self) -> list[str]:
        return ["satellite_eo_tool", "pfz_advisory_tool"]

    async def execute(self, input_data: AgentInput, tools: dict[str, BaseTool], **kwargs: Any) -> AgentOutput:
        tool_name = "satellite_eo_tool"
        messages = [f"{self.name} activated. Objective: Collect satellite SST, chlorophyll, and PFZ suitability."]
        
        if tool_name not in tools:
            err = f"Required tool '{tool_name}' not available."
            return AgentOutput(agent_name=self.name, status="failed", errors=[err], messages=messages)

        try:
            tool = tools[tool_name]
            evidence = await tool.execute(
                latitude=input_data.latitude, 
                longitude=input_data.longitude,
                agent_name=self.name
            )
            
            # Execute PFZ advisory tool if present in available tools
            if "pfz_advisory_tool" in tools:
                pfz_tool = tools["pfz_advisory_tool"]
                raw_q = input_data.context.get("raw_query", "")
                sem_q = input_data.context.get("query_semantics")
                pfz_evidence = await pfz_tool.execute(
                    latitude=input_data.latitude,
                    longitude=input_data.longitude,
                    agent_name=self.name,
                    query=raw_q,
                    query_semantics=sem_q,
                    max_distance_km=input_data.context.get("max_distance_km")
                )
                evidence.extend(pfz_evidence)

            messages.append("Satellite Earth Observation and PFZ suitability metrics collected.")
            return AgentOutput(
                agent_name=self.name,
                status="completed",
                evidence=evidence,
                messages=messages
            )
        except Exception as e:
            err_msg = f"Satellite tool error: {str(e)}"
            return AgentOutput(agent_name=self.name, status="failed", errors=[err_msg], messages=messages)
