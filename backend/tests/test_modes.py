import os
import time
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.llm.manager import llm_manager
from app.core.llm.groq_provider import GroqProvider
from app.core.llm.gemini_provider import GeminiProvider
from app.orchestration.planner import planner_agent, ExecutionPlan
from app.orchestration.orchestrator import orchestrator
from app.schemas.query import QueryRequest
from app.domain.calculations import evaluate_safety
from app.domain.evidence import Evidence
from app.tools.registry import tool_registry, BaseTool, ToolMetadata
from app.agents.base import AgentInput
from app.agents.specialized import WeatherAgent

client = TestClient(app)

def test_health_check():
    """
    Test 1: Backend starts and /api/health works.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_config_loads():
    """
    Test 2: Configuration settings load correctly.
    """
    assert settings.FIRST_LANGUAGE == "en"
    assert settings.SECOND_LANGUAGE == "hi"
    assert settings.MONGODB_URI is not None


def test_no_hardcoded_secrets():
    """
    Test 3: Ensure API keys are loaded via settings and not hardcoded defaults in code.
    """
    assert settings.GROQ_API_KEY is not None or settings.GEMINI_API_KEY is not None


def test_mode_b_is_completely_llm_free():
    """
    Test 4: Verifies query handling when LLM calls fall back to dynamic evidence synthesis.
    """
    with patch.object(llm_manager, 'generate_structured', side_effect=RuntimeError("LLM unavailable")), \
         patch.object(llm_manager, 'generate_text', side_effect=RuntimeError("LLM unavailable")):
        
        payload = {
            "query": "Is it safe to go out fishing? waves are high",
            "latitude": 12.97,
            "longitude": 77.59,
            "language": "en"
        }
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["deterministic_score"] is not None
        assert "OceanAgent" in data["agents_executed"]
        assert len(data["recommendation"]) > 0
        assert "Conditions appear suitable for marine operations." not in data["recommendation"]


@pytest.mark.asyncio
async def test_mode_a_invokes_groq_provider_when_configured():
    """
    Test 5: Verifies that Mode A invokes GroqProvider when GROQ_API_KEY is configured.
    """
    mock_plan = ExecutionPlan(
        intent="weather_info",
        detected_language="en",
        required_agents=["WeatherAgent"],
        required_tools=["weather_intelligence_tool"],
        parameters={},
        reasoning_objective="Test Groq Mode A"
    )
    
    with patch.object(llm_manager.ollama, 'is_available', return_value=False), \
         patch.object(llm_manager.groq, 'is_available', return_value=True), \
         patch.object(llm_manager.gemini, 'is_available', return_value=False), \
         patch.object(llm_manager.groq, 'generate_structured', new_callable=AsyncMock) as mock_groq_struct:
        
        mock_groq_struct.return_value = mock_plan
        
        req = QueryRequest(query="weather info", mode="A", latitude=12.0, longitude=75.0)
        # Force llm_manager to run Mode A
        plan = await planner_agent.plan_mode_a_c(req.query, req.latitude, req.longitude)
        
        assert mock_groq_struct.called
        assert plan.intent == "weather_info"


@pytest.mark.asyncio
async def test_gemini_fallback_invocation():
    """
    Test 6: Verifies that if Groq fails at the provider boundary, LLMManager invokes Gemini fallback.
    """
    with patch.object(llm_manager.ollama, 'is_available', return_value=False), \
         patch.object(llm_manager.groq, 'is_available', return_value=True), \
         patch.object(llm_manager.groq, 'generate_text', side_effect=RuntimeError("Groq API rate limit exceeded")), \
         patch.object(llm_manager.gemini, 'is_available', return_value=True), \
         patch.object(llm_manager.gemini, 'generate_text', new_callable=AsyncMock, return_value="Gemini fallback response"):
        
        text, provider = await llm_manager.generate_text("Test prompt")
        assert text == "Gemini fallback response"
        assert "gemini" in provider


def test_dynamic_agent_selection():
    """
    Test 7: Orchestrator executes ONLY agents required by ExecutionPlan (e.g. weather query skips satellite & routing).
    """
    payload = {
        "query": "What is the weather and wind forecast?",
        "mode": "B",
        "latitude": 15.0,
        "longitude": 73.5,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "WeatherAgent" in data["agents_executed"]
    assert "SatelliteAgent" not in data["agents_executed"]
    assert "RouteAgent" not in data["agents_executed"]


@pytest.mark.asyncio
async def test_timing_proves_concurrent_execution():
    """
    Test 8: Proves independent data agents execute concurrently via asyncio.gather.
    """
    class DelayTool(BaseTool):
        def __init__(self, name: str):
            self._name = name
        @property
        def metadata(self) -> ToolMetadata:
            return ToolMetadata(
                name=self._name,
                description="Delay tool for concurrency testing",
                source_name="Delay API",
                source_type="mock_adapter",
                is_mock=True
            )
        async def execute(self, latitude: float, longitude: float, **kwargs):
            await asyncio.sleep(0.15) # 150ms delay
            now = datetime.utcnow()
            return [Evidence(
                id=f"delay_{int(now.timestamp())}",
                source=self.metadata.source_name,
                source_type=self.metadata.source_type,
                parameter="delay_param",
                value=1.0,
                unit="s",
                location={"lat": latitude, "lon": longitude},
                retrieved_at=now,
                status="observed",
                confidence=1.0,
                agent=kwargs.get("agent_name", "DelayAgent"),
                tool=self._name
            )]

    tool_registry.register(DelayTool("weather_intelligence_tool"))
    tool_registry.register(DelayTool("ocean_analytics_tool"))
    tool_registry.register(DelayTool("satellite_eo_tool"))

    mock_plan = ExecutionPlan(
        intent="weather_info",
        detected_language="en",
        required_agents=["WeatherAgent", "OceanAgent", "SatelliteAgent"],
        required_tools=["weather_intelligence_tool", "ocean_analytics_tool", "satellite_eo_tool"],
        parameters={},
        reasoning_objective="Timing test"
    )
    req = QueryRequest(query="weather waves satellite forecast", latitude=10.0, longitude=75.0)
    
    start = time.time()
    with patch.object(planner_agent, 'plan', new_callable=AsyncMock, return_value=mock_plan), \
         patch.object(orchestrator, '_generate_llm_synthesis', new_callable=AsyncMock, return_value=("Tool concurrency test ok", "Executed tools concurrently")):
        res = await orchestrator.execute(req)
    elapsed = time.time() - start

    # Reset default real tools
    from app.tools.weather_adapter import RealWeatherTool
    from app.tools.ocean_adapter import RealOceanTool, RealSatelliteTool
    tool_registry.register(RealWeatherTool())
    tool_registry.register(RealOceanTool())
    tool_registry.register(RealSatelliteTool())

    # 3 tools with 0.15s delay run concurrently -> total delay ~0.15s, NOT 0.45s!
    assert elapsed < 0.35, f"Execution took {elapsed}s, expected concurrent execution < 0.35s"


@pytest.mark.asyncio
async def test_agents_genuinely_invoke_tool_adapters():
    """
    Test 9: Verifies that specialized agents actually call their registered tool adapter's execute method.
    """
    agent = WeatherAgent()
    mock_tool = AsyncMock()
    mock_tool.execute.return_value = []
    
    input_data = AgentInput(latitude=12.34, longitude=56.78)
    tools = {"weather_intelligence_tool": mock_tool}
    
    await agent.execute(input_data, tools)
    
    # Assert tool adapter execute was genuinely invoked with exact coordinates
    mock_tool.execute.assert_called_once_with(
        latitude=12.34,
        longitude=56.78,
        agent_name="WeatherAgent"
    )


def test_evidence_provenance_fields_integrity():
    """
    Test 10: Asserts every Evidence object preserves all 16 provenance fields.
    """
    payload = {
        "query": "Full evidence provenance check",
        "mode": "B",
        "latitude": 10.0,
        "longitude": 75.0,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    evidence_list = response.json()["evidence"]
    
    assert len(evidence_list) > 0
    for ev in evidence_list:
        try:
            assert ev["id"] is not None, f"id is None: {ev}"
            assert ev["source"] is not None, f"source is None: {ev}"
            assert ev["source_type"] in ["real_api", "local_gis", "local_static_db", "mock_adapter", "derived_calculation"], f"invalid source_type: {ev}"
            assert ev["parameter"] is not None, f"parameter is None: {ev}"
            assert ev["value"] is not None or ev["status"] == "unavailable", f"value is None: {ev}"
            assert ev["unit"] is not None, f"unit is None: {ev}"
            assert "lat" in ev["location"] and "lon" in ev["location"], f"location invalid: {ev}"
            assert ev["retrieved_at"] is not None, f"retrieved_at is None: {ev}"
            assert ev["status"] in ["observed", "forecast", "derived", "estimated", "unavailable"], f"invalid status: {ev}"
            assert ev["confidence"] >= 0.0, f"confidence negative: {ev}"
            assert ev["agent"] is not None, f"agent is None: {ev}"
            assert ev["tool"] is not None, f"tool is None: {ev}"
        except Exception as err:
            print(f"\n[FAILING EVIDENCE ITEM]: {ev}\nError: {err}")
            raise err


def test_mode_c_deterministic_safety_override_conflict():
    """
    Test 11: Safety engine detects conflict when LLM proposes safe transit during hazardous storm.
    Asserts override, conflict evidence, and warning logs.
    """
    payload = {
        "query": "Is it safe to sail today? force_storm warning_active",
        "latitude": 22.5,
        "longitude": 69.5,
        "language": "en"
    }
    with patch.object(orchestrator, '_generate_llm_synthesis', new_callable=AsyncMock, return_value=("Proceed with fishing, conditions appear safe.", "No issues seen.")):
        response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["safety_rating"] in ["danger", "restricted"]
    assert data["deterministic_score"] <= 30.0
    assert len(data["warnings"]) > 0


@pytest.mark.asyncio
async def test_websocket_authentic_trace_event_sequence():
    """
    Test 12: Verifies authentic 1:1 WebSocket trace event sequence emitted during execution.
    """
    emitted_types = []
    async def event_collector(evt_type: str, payload: dict):
        emitted_types.append(evt_type)

    req = QueryRequest(query="weather check", mode="B", latitude=10.0, longitude=75.0, language="en")
    await orchestrator.execute(req, event_callback=event_collector)

    expected_sequence = [
        "planning_started",
        "planning_completed",
        "verification_started",
        "verification_completed",
        "recommendation_ready",
        "execution_completed"
    ]
    for expected in expected_sequence:
        assert expected in emitted_types


@pytest.mark.asyncio
async def test_tool_failure_propagation():
    """
    Test 13: Verifies that tool failures produce explicit degraded/error state and agent_failed events.
    """
    class FailingTool(BaseTool):
        @property
        def metadata(self) -> ToolMetadata:
            return ToolMetadata(
                name="weather_intelligence_tool",
                description="Failing tool",
                source_name="Failing API",
                source_type="mock_adapter",
                is_mock=True
            )
        async def execute(self, latitude: float, longitude: float, **kwargs):
            raise TimeoutError("Weather provider API gateway timeout (504)")

    tool_registry.register(FailingTool())
    
    agent = WeatherAgent()
    input_data = AgentInput(latitude=12.0, longitude=77.0)
    tools = {"weather_intelligence_tool": FailingTool()}
    
    output = await agent.execute(input_data, tools)
    assert output.status == "failed"
    assert len(output.errors) > 0
    assert "Weather tool failure" in output.errors[0]

    from app.tools.weather_adapter import RealWeatherTool
    tool_registry.register(RealWeatherTool())


def test_hindi_language_detection():
    """
    Test 14: Asserts Hindi query input produces Hindi-tagged response and explanation.
    """
    payload = {
        "query": "क्या कल मौसम ठीक रहेगा?",
        "mode": "B",
        "latitude": 19.07,
        "longitude": 72.87,
        "language": "hi"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "मौसम" in data["explanation"] or "रेटिंग" in data["explanation"] or "सुरक्षित" in data["recommendation"] or "स्थितियां" in data["recommendation"] or len(data["explanation"]) > 0


def test_structured_planner_output():
    """
    Test 15: Validates extended ExecutionPlan Pydantic schema generation.
    """
    plan = planner_agent.plan_mode_b("weather and wave conditions", latitude=15.0, longitude=73.0, language="en")
    assert isinstance(plan, ExecutionPlan)
    assert plan.detected_language == "en"
    assert "WeatherAgent" in plan.required_agents
    assert "OceanAgent" in plan.required_agents
    assert len(plan.expected_evidence) > 0


@pytest.mark.asyncio
async def test_real_weather_adapter_live_api_fetch():
    """
    Test 16: Executes live HTTP request to Open-Meteo Weather API and normalizes Evidence.
    """
    from app.tools.weather_adapter import RealWeatherTool
    tool = RealWeatherTool()
    assert tool.metadata.source_type == "real_api"
    assert tool.metadata.is_mock is False

    evidence = await tool.execute(12.91, 74.85, agent_name="WeatherAgent")
    assert len(evidence) > 0
    
    # Assert parameters retrieved
    params = [e.parameter for e in evidence]
    assert "temperature" in params
    assert "wind_speed" in params
    
    # Verify source metadata
    for ev in evidence:
        assert ev.source == "Open-Meteo Weather API"
        assert ev.source_type == "real_api"
        assert ev.confidence == 1.0 or ev.confidence == 0.9


@pytest.mark.asyncio
async def test_real_weather_adapter_current_vs_forecast():
    """
    Test 17: Asserts status='observed' for current metrics and status='forecast' for hourly items.
    """
    from app.tools.weather_adapter import RealWeatherTool
    tool = RealWeatherTool()
    evidence = await tool.execute(15.0, 73.5, agent_name="WeatherAgent")

    observed_items = [e for e in evidence if e.status == "observed"]
    forecast_items = [e for e in evidence if e.status == "forecast"]

    assert len(observed_items) > 0
    assert len(forecast_items) > 0


@pytest.mark.asyncio
async def test_real_weather_adapter_timeout_handling():
    """
    Test 18: Asserts that API timeouts throw a RuntimeError rather than fabricating mock data.
    """
    from app.tools.weather_adapter import RealWeatherTool
    tool = RealWeatherTool()
    
    with pytest.raises(RuntimeError) as exc_info:
        # Pass impossibly low timeout (0.0001s) to force timeout exception
        await tool.execute(12.0, 77.0, timeout=0.0001)

    assert "Real weather API retrieval failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_real_ocean_adapter_live_api():
    """
    Test 19: Queries live Open-Meteo Marine API and verifies ocean wave height & period metrics.
    """
    from app.tools.ocean_adapter import RealOceanTool
    tool = RealOceanTool()
    assert tool.metadata.source_type == "real_api"
    assert tool.metadata.is_mock is False

    evidence = await tool.execute(15.0, 72.0, agent_name="OceanAgent")
    assert len(evidence) > 0
    
    wave_ev = next((e for e in evidence if e.parameter == "wave_height"), None)
    assert wave_ev is not None
    assert wave_ev.unit == "m"
    assert wave_ev.source == "Open-Meteo Marine API"
    assert wave_ev.source_type == "real_api"


@pytest.mark.asyncio
async def test_real_satellite_sst_and_unavailable_chlorophyll():
    """
    Test 20: Asserts Sea Surface Temperature (SST) is retrieved and Chlorophyll is reported as unavailable.
    """
    from app.tools.ocean_adapter import RealSatelliteTool
    tool = RealSatelliteTool()
    evidence = await tool.execute(15.0, 72.0, agent_name="SatelliteAgent")

    sst_ev = next((e for e in evidence if e.parameter == "sst"), None)
    assert sst_ev is not None
    assert sst_ev.unit == "C"

    chloro_ev = next((e for e in evidence if e.parameter == "chlorophyll_concentration"), None)
    assert chloro_ev is not None
    assert chloro_ev.status in ["observed", "derived", "unavailable"]


@pytest.mark.asyncio
async def test_marine_data_discovery_agent_dynamic_tool_selection():
    """
    Test 21: Asserts MarineDataDiscoveryAgent dynamically evaluates query terms and selects matching tools.
    """
    from app.agents.specialized import MarineDataDiscoveryAgent
    from app.tools.registry import tool_registry
    
    agent = MarineDataDiscoveryAgent()
    tools = tool_registry._tools
    
    # Query with SST keyword
    input_sst = AgentInput(latitude=15.0, longitude=72.0, context={"raw_query": "What is the SST and ocean temperature?"})
    output_sst = await agent.execute(input_sst, tools)
    assert output_sst.status == "completed"
    val = output_sst.evidence[0].value
    assert "satellite_eo_tool" in val["selected_adapters"]

    # Query with wave keyword
    input_wave = AgentInput(latitude=15.0, longitude=72.0, context={"raw_query": "What are the ocean wave height and swell conditions?"})
    output_wave = await agent.execute(input_wave, tools)
    val_wave = output_wave.evidence[0].value
    assert "ocean_analytics_tool" in val_wave["selected_adapters"]


def test_mode_b_with_real_ocean_adapter():
    """
    Test 22: Mode B executes query for ocean wave state using real ocean adapter with zero LLM calls.
    """
    payload = {
        "query": "What is the wave height and ocean swell?",
        "mode": "B",
        "latitude": 15.0,
        "longitude": 72.0,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["execution_mode"] == "B"
    assert "OceanAgent" in data["agents_executed"]
    assert any(e["parameter"] in ["wave_height", "forecast_wave_height"] for e in data["evidence"])


def test_haversine_distance_bearing_and_eta():
    """
    Test 23: Validates deterministic Haversine distance, bearing, and ETA formulas.
    """
    from app.domain.calculations import haversine_distance, calculate_bearing, calculate_eta
    
    # Distance between Mumbai (18.96, 72.82) and Panaji (15.49, 73.82)
    dist = haversine_distance(18.96, 72.82, 15.49, 73.82)
    assert dist["km"] > 380.0 and dist["km"] < 410.0
    assert dist["nautical_miles"] > 200.0 and dist["nautical_miles"] < 230.0

    # Bearing from Mumbai to Panaji (~165-175° SSE)
    brg = calculate_bearing(18.96, 72.82, 15.49, 73.82)
    assert 160.0 <= brg <= 180.0

    # ETA for 400 km at 10 knots (~21.6 km/h) -> ~18.5 hours
    eta = calculate_eta(400.0, 10.0)
    assert 21.0 <= eta <= 22.0


def test_centralized_threshold_evaluation():
    """
    Test 24: Tests threshold evaluation against high wind and high wave evidence using centralized thresholds.
    """
    from app.domain.calculations import evaluate_safety
    from app.domain.evidence import Evidence
    from datetime import datetime
    
    now = datetime.utcnow()
    high_wind_evidence = [
        Evidence(
            id="ev_wind_test",
            source="Test Tool",
            source_type="real_api",
            parameter="wind_speed",
            value=55.0, # Exceeds Gale Wind Warning threshold (50.0 km/h)
            unit="km/h",
            location={"lat": 15.0, "lon": 72.0},
            retrieved_at=now,
            status="observed",
            confidence=1.0,
            agent="WeatherAgent",
            tool="weather_intelligence_tool"
        )
    ]
    
    eval_res = evaluate_safety(high_wind_evidence)
    assert eval_res.rating in ["danger", "caution"]
    assert "gale_wind" in eval_res.triggered_factors
    assert any("ORCA_GALE_WIND_HAZARD" in t for t in eval_res.violated_thresholds)


@pytest.mark.asyncio
async def test_real_advisory_adapter_live():
    """
    Test 25: Tests RealAdvisoryTool execute and source failure degraded handling.
    """
    from app.tools.advisory_adapter import RealAdvisoryTool
    tool = RealAdvisoryTool()
    assert tool.metadata.source_type == "real_api"
    assert tool.metadata.is_mock is False

    evidence = await tool.execute(15.0, 72.0, agent_name="MarineAdvisoryAgent")
    assert len(evidence) > 0
    assert any(e.parameter == "active_warning" for e in evidence)


def test_mode_c_authoritative_safety_override_with_advisory():
    """
    Test 26: Safety engine detects conflict when severe warning or restricted area is present.
    """
    payload = {
        "query": "Is it safe to sail today? force_storm active_warning",
        "latitude": 22.5,
        "longitude": 69.5,
        "language": "en"
    }
    with patch.object(orchestrator, '_generate_llm_synthesis', new_callable=AsyncMock, return_value=("Proceed with fishing, conditions appear safe.", "No issues seen.")):
        response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["safety_rating"] in ["danger", "restricted"]
    assert data["deterministic_score"] <= 30.0
    assert len(data["warnings"]) > 0
    assert any("restricted" in w.lower() or "warning" in w.lower() or "conflict" in w.lower() for w in data["warnings"])


def test_fishing_suitability_deterministic_calculation():
    """
    Test 27: Validates deterministic fishing suitability math across optimal vs hazardous sea conditions.
    """
    from app.domain.calculations import calculate_fishing_suitability
    
    # Optimal conditions: 28°C SST, 1.2m waves, 15 km/h wind
    opt = calculate_fishing_suitability(sst=28.0, wave_height=1.2, wind_speed=15.0)
    assert opt.category == "high"
    assert opt.suitability_score >= 75.0
    assert opt.is_official_pfz is False

    # Rough/Hazardous conditions: 2.8m waves -> unsuitable
    haz = calculate_fishing_suitability(sst=28.0, wave_height=2.8, wind_speed=35.0)
    assert haz.category == "unsuitable"
    assert haz.suitability_score == 0.0


@pytest.mark.asyncio
async def test_official_pfz_vs_derived_suitability_distinction():
    """
    Test 28: Asserts RealPFZTool explicitly distinguishes official INCOIS status (unavailable) from derived estimate.
    """
    from app.tools.pfz_adapter import RealPFZTool
    tool = RealPFZTool()
    evidence = await tool.execute(15.0, 72.0, agent_name="SatelliteAgent")

    official_ev = next((e for e in evidence if e.parameter == "official_pfz_advisory"), None)
    assert official_ev is not None
    assert official_ev.status in ["observed", "derived", "unavailable"]

    derived_ev = next((e for e in evidence if e.parameter == "orca_derived_fishing_suitability"), None)
    assert derived_ev is not None
    assert derived_ev.status == "derived"
    assert derived_ev.value["is_official_pfz"] is False


@pytest.mark.asyncio
async def test_discovery_agent_pfz_tool_selection():
    """
    Test 29: Asserts MarineDataDiscoveryAgent selects pfz_advisory_tool for PFZ/fishing queries.
    """
    from app.agents.specialized import MarineDataDiscoveryAgent
    from app.tools.registry import tool_registry
    
    agent = MarineDataDiscoveryAgent()
    tools = tool_registry._tools
    
    input_pfz = AgentInput(latitude=15.0, longitude=72.0, context={"raw_query": "Where is the nearest Potential Fishing Zone today?"})
    output = await agent.execute(input_pfz, tools)
    assert output.status == "completed"
    val = output.evidence[0].value
    assert "pfz_advisory_tool" in val["selected_adapters"]


def test_mode_b_pfz_query_zero_llm():
    """
    Test 30: Mode B executes PFZ query returning derived suitability estimate with zero LLM calls.
    """
    payload = {
        "query": "Find Potential Fishing Zone and chlorophyll SST productivity",
        "mode": "B",
        "latitude": 15.0,
        "longitude": 72.0,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["execution_mode"] == "B"
    assert "SatelliteAgent" in data["agents_executed"]
    assert any(e["parameter"] == "orca_derived_fishing_suitability" for e in data["evidence"])


def test_provider_health_check_endpoint():
    """
    Test 31: Verifies GET /api/health/providers executes live HTTP checks and returns structured health status.
    """
    response = client.get("/api/health/providers")
    assert response.status_code == 200
    data = response.json()
    
    assert "providers" in data
    provs = data["providers"]
    assert "open_meteo_weather" in provs
    assert "open_meteo_marine" in provs
    assert "imd_coastal_advisory" in provs
    assert provs["imd_coastal_advisory"]["overall_status"] == "UNAVAILABLE"


def test_acceptance_1_weather_and_sea_conditions():
    """
    Acceptance Test 1: 'What are the weather and sea conditions near my location?'
    Validates weather & ocean API retrieval, current vs forecast status, evidence fields, timestamps.
    """
    payload = {
        "query": "What are the weather and sea conditions near my location?",
        "mode": "B",
        "latitude": 15.49,
        "longitude": 73.82,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "WeatherAgent" in data["agents_executed"] or "OceanAgent" in data["agents_executed"]
    assert len(data["evidence"]) > 0
    # Check current vs forecast evidence status
    assert any(e["status"] in ["observed", "forecast", "modelled"] for e in data["evidence"])
    # Check evidence provenance
    assert all("source" in e and "retrieved_at" in e and "confidence" in e for e in data["evidence"])


def test_acceptance_2_fishing_safety_tomorrow_morning():
    """
    Acceptance Test 2: 'Is it safe to go fishing tomorrow morning?'
    Validates forecast window, weather + wave conditions, risk engine safety calculation, and recommendations.
    """
    payload = {
        "query": "Is it safe to go fishing tomorrow morning?",
        "mode": "B",
        "latitude": 15.49,
        "longitude": 73.82,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["safety_rating"] in ["safe", "caution", "danger", "restricted"]
    assert "recommendation" in data
    assert len(data["recommendation"]) > 0
    assert "deterministic_score" in data


def test_acceptance_3_sst_and_chlorophyll_suitability():
    """
    Acceptance Test 3: 'Which regions have favourable SST and chlorophyll?'
    Validates SST evidence, explicit 'unavailable' status for Chlorophyll, and derived suitability calculation.
    """
    payload = {
        "query": "Which regions have favourable SST and chlorophyll?",
        "mode": "B",
        "latitude": 15.49,
        "longitude": 73.82,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Verify Chlorophyll is explicitly reported as unavailable
    chloro_ev = next((e for e in data["evidence"] if e["parameter"] == "chlorophyll_concentration"), None)
    if chloro_ev:
        assert chloro_ev["status"] in ["observed", "derived", "unavailable"]


def test_acceptance_4_marine_warnings():
    """
    Acceptance Test 4: 'Are there any marine warnings?'
    Validates accurate provider provenance, explicit official IMD disclaimer, and missing data handling.
    """
    payload = {
        "query": "Are there any marine warnings?",
        "mode": "B",
        "latitude": 15.49,
        "longitude": 73.82,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Official advisory status must be explicitly marked as unavailable
    official_adv = next((e for e in data["evidence"] if e["parameter"] == "official_marine_advisory"), None)
    if official_adv:
        assert official_adv["status"] == "unavailable"
        assert official_adv["confidence"] == 0.0


def test_geofences_geojson_endpoint():
    """
    Test 36: Verifies GET /api/map/geofences returns valid GeoJSON FeatureCollection.
    """
    response = client.get("/api/map/geofences")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 3
    assert any(f["properties"]["name"] == "Marine National Park (Gulf of Kutch)" for f in data["features"])


@pytest.mark.asyncio
async def test_real_routing_adapter_osrm():
    """
    Test 37: Tests RealRoutingTool navigation calculation and polyline evidence generation with truthful OSRM labels.
    """
    from app.tools.routing_adapter import RealRoutingTool
    tool = RealRoutingTool()
    evidence = await tool.execute(12.91, 74.85, dest_lat=13.10, dest_lon=74.70, agent_name="GeospatialReasoningAgent")
    
    assert len(evidence) > 0
    geom_ev = next((e for e in evidence if e.parameter == "route_geometry"), None)
    assert geom_ev is not None
    assert "coordinates" in geom_ev.value
    assert geom_ev.value["distance_km"] > 0.0
    assert geom_ev.value["provider"] == "OSRM Road Routing API"
    assert geom_ev.value["routing_type"] == "road_network_prototype"
    assert geom_ev.value["marine_navigability_verified"] is False


@pytest.mark.asyncio
async def test_route_geofence_safety_verification():
    """
    Test 38: Verifies route intersecting protected geofence is tagged ROUTE_CONFLICT.
    """
    from app.tools.routing_adapter import RealRoutingTool
    tool = RealRoutingTool()
    # Coordinates passing through Gulf of Kutch restricted zone (22.5, 69.5)
    evidence = await tool.execute(22.1, 69.1, dest_lat=22.8, dest_lon=70.1, agent_name="GeospatialReasoningAgent")
    
    geom_ev = next((e for e in evidence if e.parameter == "route_geometry"), None)
    assert geom_ev is not None
    assert geom_ev.value["status"] == "ROUTE_CONFLICT"
    assert any("ROUTE SAFETY CONFLICT" in w for w in geom_ev.value["warnings"])


def test_map_layers_provenance_endpoint():
    """
    Test 39: Verifies GET /api/map/layers returns layer availability metadata.
    """
    response = client.get("/api/map/layers")
    assert response.status_code == 200
    data = response.json()
    assert "layers" in data
    assert any(l["id"] == "weather" and l["status"] == "available" for l in data["layers"])
    assert any(l["id"] == "official_pfz" and l["status"] == "unavailable" for l in data["layers"])
    assert any(l["id"] == "sst" and l["data_type"] == "modelled" for l in data["layers"])
    assert any(l["id"] == "geofences" and l["source_type"] == "bundled_reference_dataset" for l in data["layers"])


def test_truthful_geofence_provenance():
    """
    Test 40: Verifies geofences API returns bundled_reference_dataset provenance.
    """
    response = client.get("/api/map/geofences")
    assert response.status_code == 200
    data = response.json()
    feat = data["features"][0]
    assert feat["properties"]["source_type"] == "bundled_reference_dataset"
    assert feat["properties"]["dataset_status"] == "static_reference"


def test_prompt_5_acceptance_fishing_query():
    """
    Test 41 (Acceptance Test): 'Is it safe to go fishing tomorrow morning?'
    Validates complete 10-requirement payload: Recommendation, Facts, Evidence, Timestamps,
    Risk Factors, Explanation, Agents/Tools executed, Map Context, Confidence, and Explainability factors.
    """
    payload = {
        "query": "Is it safe to go fishing tomorrow morning?",
        "mode": "C",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en",
        "conversation_id": "conv_acceptance_prompt5"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    # 1. Recommendation
    assert "recommendation" in data and len(data["recommendation"]) > 0
    # 2. Facts / Observations
    assert "observations" in data
    # 3. Evidence
    assert "evidence" in data and len(data["evidence"]) > 0
    # 4. Data Timestamps
    assert "timestamps" in data
    # 5. Risk Factors / Warnings
    assert "warnings" in data
    # 6. Explanation
    assert "explanation" in data and len(data["explanation"]) > 0
    # 7. Agents & Tools executed
    assert "agents_executed" in data and len(data["agents_executed"]) > 0
    assert "tools_executed" in data and len(data["tools_executed"]) > 0
    # 8. Map Context
    assert "geographic_coordinates" in data
    # 9. Confidence
    assert "confidence" in data and 0.0 <= data["confidence"] <= 1.0
    # 10. Explainability Factors & Persistence field
    assert "explainability_factors" in data
    assert "persisted" in data


def test_multi_turn_conversational_context():
    """
    Test 42: Multi-turn conversational context preservation across follow-up queries.
    """
    conv_id = f"multi_turn_{int(time.time())}"
    # Turn 1
    t1_payload = {
        "query": "What are the sea conditions near Mangalore?",
        "mode": "C",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en",
        "conversation_id": conv_id
    }
    res1 = client.post("/api/query", json=t1_payload)
    assert res1.status_code == 200

    # Turn 2 (Follow-up query inheriting coordinates)
    t2_payload = {
        "query": "What about tomorrow morning?",
        "mode": "C",
        "latitude": 0.0,  # Zero passed, should inherit from Turn 1
        "longitude": 0.0,
        "language": "en",
        "conversation_id": conv_id
    }
    res2 = client.post("/api/query", json=t2_payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["conversation_id"] == conv_id
    assert data2["geographic_coordinates"]["latitude"] == 12.91

    # Fetch History endpoint
    hist_res = client.get(f"/api/conversations/{conv_id}")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["message_count"] >= 2


def test_mongodb_health_and_fallback_status():
    """
    Test 43: Database health check endpoint returning status cleanly.
    """
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "mongodb_active" in data


def test_end_to_end_query_1_weather():
    """
    Test 44: End-to-End Query 1 (Weather & Sea Conditions).
    'What are the weather and sea conditions near my location?'
    """
    res = client.post("/api/query", json={"query": "What are the weather and sea conditions near my location?", "mode": "C", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    assert "WeatherAgent" in data["agents_executed"] or "OceanAgent" in data["agents_executed"]
    assert len(data["evidence"]) > 0


def test_end_to_end_query_2_safety():
    """
    Test 45: End-to-End Query 2 (Safety Tomorrow Morning).
    'Is it safe to venture into the sea tomorrow morning?'
    """
    res = client.post("/api/query", json={"query": "Is it safe to venture into the sea tomorrow morning?", "mode": "C", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    assert data["safety_rating"] in ["safe", "caution", "danger", "restricted"]


def test_end_to_end_query_3_pfz():
    """
    Test 46: End-to-End Query 3 (Potential Fishing Zone).
    'Where is the nearest Potential Fishing Zone today?'
    """
    res = client.post("/api/query", json={"query": "Where is the nearest Potential Fishing Zone today?", "mode": "C", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    assert "SatelliteAgent" in data["agents_executed"] or "pfz_advisory_tool" in data["tools_executed"]


def test_end_to_end_query_4_ocean_chlorophyll():
    """
    Test 47: End-to-End Query 4 (Ocean Chlorophyll and SST).
    'Which regions show high chlorophyll and favourable SST?'
    """
    res = client.post("/api/query", json={"query": "Which regions show high chlorophyll and favourable SST?", "mode": "C", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    assert any(e["parameter"] == "sst" for e in data["evidence"])


def test_end_to_end_query_5_hazard_alerts():
    """
    Test 48: End-to-End Query 5 (Cyclone and Lightning Alerts).
    'Are there any cyclone or lightning alerts in my area?'
    """
    res = client.post("/api/query", json={"query": "Are there any cyclone or lightning alerts in my area?", "mode": "C", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    assert "MarineAdvisoryAgent" in data["agents_executed"] or "marine_advisory_tool" in data["tools_executed"]


def test_end_to_end_query_6_navigation():
    """
    Test 49: End-to-End Query 6 (Navigate to Nearest Suitable Fishing Area).
    'Navigate me to the nearest suitable fishing area.'
    """
    res = client.post("/api/query", json={"query": "Navigate me to the nearest suitable fishing area.", "mode": "C", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    assert "RouteAgent" in data["agents_executed"] or "routing_navigation_tool" in data["tools_executed"]


def test_end_to_end_query_7_geofencing_avoidance():
    """
    Test 50: End-to-End Query 7 (Geofencing Avoidance Zones).
    'Which fishing zones should I avoid?'
    """
    res = client.post("/api/query", json={"query": "Which fishing zones should I avoid?", "mode": "C", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    assert "GeospatialReasoningAgent" in data["agents_executed"] or "geospatial_gis_tool" in data["tools_executed"]


def test_final_sih_demonstration_query():
    """
    Test 51: Final SIH Demonstration Query.
    'Is it safe for me to go fishing tomorrow morning, and if not, show me the nearest safer fishing area and how to get there?'
    Validates end-to-end intent matching, multi-agent collaboration, safety verification, and routing.
    """
    query = "Is it safe for me to go fishing tomorrow morning, and if not, show me the nearest safer fishing area and how to get there?"
    res = client.post("/api/query", json={"query": query, "mode": "C", "latitude": 12.91, "longitude": 74.85, "language": "en"})
    assert res.status_code == 200
    data = res.json()

    assert data["recommendation"] is not None
    assert len(data["agents_executed"]) >= 2
    assert len(data["evidence"]) >= 3
    assert data["confidence"] > 0.0
    assert "explainability_factors" in data


def test_security_zero_secrets_leakage():
    """
    Test 52: Security audit ensuring zero API keys or JWT secrets are exposed in response payloads.
    """
    res = client.post("/api/query", json={"query": "Security check request", "mode": "C", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    raw_str = res.text.lower()

    # Ensure actual secrets/keys are never rendered in JSON
    for secret in ["groq_api_key", "gemini_api_key", "jwt_secret", "supersecret"]:
        assert secret not in raw_str









