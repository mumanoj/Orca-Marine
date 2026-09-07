import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Optional, Literal
from pydantic import BaseModel
from app.domain.evidence import Evidence
from app.core.config import settings

class ToolMetadata(BaseModel):
    name: str
    description: str
    source_name: str
    source_type: Literal["real_api", "local_gis", "mock_adapter", "derived_calculation"]
    source_url: Optional[str] = None
    is_mock: bool

class BaseTool(ABC):
    """
    Abstract Base Class for all ORCA Tools.
    """
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        pass

    @abstractmethod
    async def execute(self, latitude: float, longitude: float, **kwargs: Any) -> list[Evidence]:
        """
        Execute the tool for a given coordinate. Returns a list of structured Evidence.
        """
        pass


class MockWeatherTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock_weather_tool",
            description="Fetches weather forecast (mock adapter for validation).",
            source_name="Open-Meteo Weather API Mock",
            source_type="mock_adapter",
            source_url=f"{settings.WEATHER_API_BASE_URL}?mock=true",
            is_mock=True
        )

    async def execute(self, latitude: float, longitude: float, **kwargs: Any) -> list[Evidence]:
        now = datetime.utcnow()
        # Generates static test forecast data
        return [
            Evidence(
                id=f"wea_{int(now.timestamp())}_temp",
                source=self.metadata.source_name,
                source_url=self.metadata.source_url,
                source_type=self.metadata.source_type,
                parameter="temperature",
                value=28.5,
                unit="C",
                location={"lat": latitude, "lon": longitude},
                observed_at=now,
                retrieved_at=now,
                valid_from=now,
                valid_until=now + timedelta(hours=12),
                status="forecast",
                confidence=0.9,
                agent=kwargs.get("agent_name", "WeatherAgent"),
                tool=self.metadata.name
            ),
            Evidence(
                id=f"wea_{int(now.timestamp())}_wind",
                source=self.metadata.source_name,
                source_url=self.metadata.source_url,
                source_type=self.metadata.source_type,
                parameter="wind_speed",
                value=22.0, # km/h (moderate wind)
                unit="km/h",
                location={"lat": latitude, "lon": longitude},
                observed_at=now,
                retrieved_at=now,
                valid_from=now,
                valid_until=now + timedelta(hours=12),
                status="forecast",
                confidence=0.85,
                agent=kwargs.get("agent_name", "WeatherAgent"),
                tool=self.metadata.name
            ),
            Evidence(
                id=f"wea_{int(now.timestamp())}_precip",
                source=self.metadata.source_name,
                source_url=self.metadata.source_url,
                source_type=self.metadata.source_type,
                parameter="precipitation_probability",
                value=15.0, # 15%
                unit="%",
                location={"lat": latitude, "lon": longitude},
                observed_at=now,
                retrieved_at=now,
                valid_from=now,
                valid_until=now + timedelta(hours=12),
                status="forecast",
                confidence=0.9,
                agent=kwargs.get("agent_name", "WeatherAgent"),
                tool=self.metadata.name
            )
        ]


class MockOceanTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock_ocean_tool",
            description="Fetches ocean state (wave heights, period, tides; mock adapter for validation).",
            source_name="Open-Meteo Marine API Mock",
            source_type="mock_adapter",
            source_url=f"{settings.MARINE_API_BASE_URL}?mock=true",
            is_mock=True
        )

    async def execute(self, latitude: float, longitude: float, **kwargs: Any) -> list[Evidence]:
        now = datetime.utcnow()
        # Generates test wave metrics
        # If user query implies stormy weather, we can adjust value via kwargs for testing C conflict detection
        wave_height = kwargs.get("wave_height", 1.2) # meters
        return [
            Evidence(
                id=f"oce_{int(now.timestamp())}_wave",
                source=self.metadata.source_name,
                source_url=self.metadata.source_url,
                source_type=self.metadata.source_type,
                parameter="wave_height",
                value=wave_height,
                unit="m",
                location={"lat": latitude, "lon": longitude},
                observed_at=now,
                retrieved_at=now,
                valid_from=now,
                valid_until=now + timedelta(hours=6),
                status="forecast",
                confidence=0.8,
                agent=kwargs.get("agent_name", "OceanAgent"),
                tool=self.metadata.name
            ),
            Evidence(
                id=f"oce_{int(now.timestamp())}_wave_period",
                source=self.metadata.source_name,
                source_url=self.metadata.source_url,
                source_type=self.metadata.source_type,
                parameter="wave_period",
                value=8.0,
                unit="s",
                location={"lat": latitude, "lon": longitude},
                observed_at=now,
                retrieved_at=now,
                valid_from=now,
                valid_until=now + timedelta(hours=6),
                status="forecast",
                confidence=0.8,
                agent=kwargs.get("agent_name", "OceanAgent"),
                tool=self.metadata.name
            )
        ]


INDIAN_MARINE_PROTECTED_AREAS = [
    {
        "name": "Netrani Island Coral Reef Sanctuary",
        "lat_min": 13.9, "lat_max": 14.2, "lon_min": 74.2, "lon_max": 74.5,
        "center": {"lat": 14.02, "lon": 74.33},
        "description": "Protected coral reef ecosystem and marine biodiversity zone. Spearfishing and non-permitted trawling prohibited."
    },
    {
        "name": "Gulf of Kutch Marine National Park",
        "lat_min": 22.0, "lat_max": 23.2, "lon_min": 69.0, "lon_max": 70.5,
        "center": {"lat": 22.6, "lon": 69.75},
        "description": "Restricted coral reef and mangrove sanctuary. Fishing prohibited under Indian Wildlife Protection Act."
    },
    {
        "name": "Gulf of Mannar Marine Biosphere Reserve",
        "lat_min": 8.6, "lat_max": 9.3, "lon_min": 78.1, "lon_max": 79.3,
        "center": {"lat": 8.95, "lon": 78.7},
        "description": "Dugong and coral conservation zone. Trawling restricted within 5 nautical miles."
    },
    {
        "name": "Sundarbans Estuarine Sanctuary",
        "lat_min": 21.5, "lat_max": 22.3, "lon_min": 88.5, "lon_max": 89.5,
        "center": {"lat": 21.9, "lon": 89.0},
        "description": "Mangrove estuarine reserve. Mechanized fishing prohibited."
    },
    {
        "name": "Gahirmatha Olive Ridley Turtle Sanctuary",
        "lat_min": 20.4, "lat_max": 20.8, "lon_min": 86.8, "lon_max": 87.2,
        "center": {"lat": 20.6, "lon": 87.0},
        "description": "Mass nesting sanctuary. All fishing prohibited Nov 1 - May 31."
    },
    {
        "name": "Palk Strait IMBL Boundary Zone",
        "lat_min": 9.8, "lat_max": 10.5, "lon_min": 79.5, "lon_max": 80.5,
        "center": {"lat": 10.15, "lon": 80.0},
        "description": "International Maritime Boundary Line. High risk of vessel interception beyond line."
    }
]

class MockGeospatialTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="geospatial_gis_tool",
            description="Performs point-in-polygon and distance checks on Indian Marine Protected Areas (IMPA & IMBL).",
            source_name="Indian Marine GIS Spatial Database (IMPA & IMBL)",
            source_type="local_gis",
            is_mock=False
        )

    async def execute(self, latitude: float, longitude: float, **kwargs: Any) -> list[Evidence]:
        now = datetime.utcnow()
        
        is_restricted = False
        matched_mpa = None
        nearby_zones = []
        
        for mpa in INDIAN_MARINE_PROTECTED_AREAS:
            c_lat = mpa["center"]["lat"]
            c_lon = mpa["center"]["lon"]
            # Haversine distance to center of MPA
            dlat = math.radians(c_lat - latitude)
            dlon = math.radians(c_lon - longitude)
            a = math.sin(dlat / 2)**2 + math.cos(math.radians(latitude)) * math.cos(math.radians(c_lat)) * math.sin(dlon / 2)**2
            d_km = round(6371.0 * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))), 1)

            is_inside = (mpa["lat_min"] <= latitude <= mpa["lat_max"] and mpa["lon_min"] <= longitude <= mpa["lon_max"])
            if is_inside:
                is_restricted = True
                matched_mpa = mpa
            
            # Include in nearby list if within 400 km or inside
            if is_inside or d_km <= 400.0:
                nearby_zones.append({
                    "name": mpa["name"],
                    "latitude": c_lat,
                    "longitude": c_lon,
                    "distance_km": d_km,
                    "description": mpa["description"],
                    "is_inside": is_inside
                })

        # Sort nearby restricted zones by distance
        nearby_zones = sorted(nearby_zones, key=lambda z: z["distance_km"])
        boundary_name = matched_mpa["name"] if matched_mpa else "None"
        boundary_desc = matched_mpa["description"] if matched_mpa else "Location is clear of active IMPA/IMBL protected boundaries."
        
        return [
            Evidence(
                id=f"geo_{int(now.timestamp())}_restriction",
                source=self.metadata.source_name,
                source_type=self.metadata.source_type,
                parameter="is_restricted_area",
                value=is_restricted,
                unit="boolean",
                location={"lat": latitude, "lon": longitude},
                retrieved_at=now,
                status="derived",
                confidence=1.0,
                agent=kwargs.get("agent_name", "GeospatialAgent"),
                tool=self.metadata.name
            ),
            Evidence(
                id=f"geo_{int(now.timestamp())}_boundary",
                source=self.metadata.source_name,
                source_type=self.metadata.source_type,
                parameter="intersecting_boundary_name",
                value=boundary_name,
                unit="string",
                location={"lat": latitude, "lon": longitude},
                retrieved_at=now,
                status="derived",
                confidence=1.0,
                agent=kwargs.get("agent_name", "GeospatialAgent"),
                tool=self.metadata.name
            ),
            Evidence(
                id=f"geo_{int(now.timestamp())}_description",
                source=self.metadata.source_name,
                source_type=self.metadata.source_type,
                parameter="boundary_description",
                value=boundary_desc,
                unit="string",
                location={"lat": latitude, "lon": longitude},
                retrieved_at=now,
                status="derived",
                confidence=1.0,
                agent=kwargs.get("agent_name", "GeospatialAgent"),
                tool=self.metadata.name
            ),
            Evidence(
                id=f"geo_{int(now.timestamp())}_nearby_restricted",
                source=self.metadata.source_name,
                source_type=self.metadata.source_type,
                parameter="nearby_restricted_zones",
                value={
                    "total_count": len(nearby_zones),
                    "restricted_zones": nearby_zones
                },
                unit="zone_list",
                location={"lat": latitude, "lon": longitude},
                retrieved_at=now,
                status="derived",
                confidence=1.0,
                agent=kwargs.get("agent_name", "GeospatialAgent"),
                tool=self.metadata.name
            )
        ]


class MockAdvisoryTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock_advisory_tool",
            description="Checks for active cyclone, lightning or warning advisories.",
            source_name="Indian Meteorological Advisory mock",
            source_type="mock_adapter",
            source_url=f"{settings.ALERT_API_BASE_URL}?mock=true",
            is_mock=True
        )

    async def execute(self, latitude: float, longitude: float, **kwargs: Any) -> list[Evidence]:
        now = datetime.utcnow()
        # For testing Mode C, let's allow forcing an active warning
        warning_active = kwargs.get("warning_active", False)
        warning_text = "Cyclone warning active for Gujarat coast" if warning_active else "No active warnings"
        
        return [
            Evidence(
                id=f"adv_{int(now.timestamp())}_alert",
                source=self.metadata.source_name,
                source_url=self.metadata.source_url,
                source_type=self.metadata.source_type,
                parameter="active_warning",
                value=warning_active,
                unit="boolean",
                location={"lat": latitude, "lon": longitude},
                observed_at=now,
                retrieved_at=now,
                status="observed",
                confidence=0.95,
                agent=kwargs.get("agent_name", "MarineAdvisoryAgent"),
                tool=self.metadata.name
            ),
            Evidence(
                id=f"adv_{int(now.timestamp())}_alert_text",
                source=self.metadata.source_name,
                source_url=self.metadata.source_url,
                source_type=self.metadata.source_type,
                parameter="warning_details",
                value=warning_text,
                unit="string",
                location={"lat": latitude, "lon": longitude},
                observed_at=now,
                retrieved_at=now,
                status="observed",
                confidence=0.95,
                agent=kwargs.get("agent_name", "MarineAdvisoryAgent"),
                tool=self.metadata.name
            )
        ]


class MockRoutingTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="routing_navigation_tool",
            description="Calculates navigation geometry, distance and ETA (mock router).",
            source_name="OSRM Route Engine Mock",
            source_type="mock_adapter",
            source_url=f"{settings.ROUTING_API_BASE_URL}?mock=true",
            is_mock=True
        )

    async def execute(self, latitude: float, longitude: float, **kwargs: Any) -> list[Evidence]:
        now = datetime.utcnow()
        dest_lat = kwargs.get("dest_lat", latitude + 0.1)
        dest_lon = kwargs.get("dest_lon", longitude + 0.1)
        
        # Simple straight line route geometry simulation
        geometry = f"LINESTRING({longitude} {latitude}, {dest_lon} {dest_lat})"
        distance_km = 15.6 # mock
        duration_mins = 45.0 # mock
        
        return [
            Evidence(
                id=f"rt_{int(now.timestamp())}_geom",
                source=self.metadata.source_name,
                source_url=self.metadata.source_url,
                source_type=self.metadata.source_type,
                parameter="route_geometry",
                value={"geometry": geometry, "distance_km": distance_km, "duration_mins": duration_mins},
                unit="mixed",
                location={"lat": latitude, "lon": longitude},
                retrieved_at=now,
                status="derived",
                confidence=1.0,
                agent=kwargs.get("agent_name", "RouteAgent"),
                tool=self.metadata.name
            )
        ]


class MockSatelliteTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock_satellite_tool",
            description="Fetches satellite Chlorophyll-a concentration and Sea Surface Temperature (mock).",
            source_name=f"Copernicus Marine ({settings.SATELLITE_PROVIDER}_adapter)",
            source_type="mock_adapter",
            is_mock=True
        )

    async def execute(self, latitude: float, longitude: float, **kwargs: Any) -> list[Evidence]:
        now = datetime.utcnow()
        return [
            Evidence(
                id=f"sat_{int(now.timestamp())}_sst",
                source=self.metadata.source_name,
                source_type=self.metadata.source_type,
                parameter="sst",
                value=27.8,
                unit="C",
                location={"lat": latitude, "lon": longitude},
                observed_at=now - timedelta(days=1), # satellite data is slightly delayed
                retrieved_at=now,
                valid_from=now - timedelta(days=1),
                valid_until=now + timedelta(days=1),
                status="observed",
                confidence=0.9,
                agent=kwargs.get("agent_name", "SatelliteAgent"),
                tool=self.metadata.name
            ),
            Evidence(
                id=f"sat_{int(now.timestamp())}_chlorophyll",
                source=self.metadata.source_name,
                source_type=self.metadata.source_type,
                parameter="chlorophyll_concentration",
                value=0.35,
                unit="mg/m3",
                location={"lat": latitude, "lon": longitude},
                observed_at=now - timedelta(days=1),
                retrieved_at=now,
                valid_from=now - timedelta(days=1),
                valid_until=now + timedelta(days=1),
                status="observed",
                confidence=0.85,
                agent=kwargs.get("agent_name", "SatelliteAgent"),
                tool=self.metadata.name
            )
        ]


class ToolRegistry:
    """
    Central Tool Registry mapping names to tool instances.
    Allows dynamic dependency injection.
    """
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        # Import real tools lazily to avoid circular imports
        from app.tools.weather_adapter import RealWeatherTool
        from app.tools.ocean_adapter import RealOceanTool, RealSatelliteTool
        from app.tools.advisory_adapter import RealAdvisoryTool
        from app.tools.pfz_adapter import RealPFZTool
        from app.tools.routing_adapter import RealRoutingTool
        
        # Register real tools & mock fallback tools
        self.register(RealWeatherTool())
        self.register(RealOceanTool())
        self.register(RealSatelliteTool())
        self.register(RealAdvisoryTool())
        self.register(RealPFZTool())
        self.register(RealRoutingTool())
        self.register(MockWeatherTool())
        self.register(MockOceanTool())
        self.register(MockGeospatialTool())
        self.register(MockAdvisoryTool())
        self.register(MockRoutingTool())
        self.register(MockSatelliteTool())

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.metadata.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> list[ToolMetadata]:
        return [tool.metadata for tool in self._tools.values()]

# Global registry
tool_registry = ToolRegistry()
