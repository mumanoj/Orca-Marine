import logging
from datetime import datetime, timedelta
from typing import Any
import httpx

from app.core.config import settings
from app.domain.evidence import Evidence
from app.domain.calculations import haversine_distance, calculate_bearing, calculate_eta
from app.tools.registry import BaseTool, ToolMetadata, MockGeospatialTool

logger = logging.getLogger(__name__)

class RealRoutingTool(BaseTool):
    """
    Production Routing Tool Adapter Prototype.
    Integrates Open Source Routing Machine (OSRM) API for prototype network path generation.
    TRUTHFULNESS NOTICE: OSRM is a road-network routing engine. Marine navigability (bathymetry, 
    shipping channels, ocean currents) is NOT verified by OSRM.
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="routing_navigation_tool",
            description="Prototype path calculation via OSRM. Marine navigability is NOT verified.",
            source_name="OSRM Road Routing API (Prototype Pipeline)",
            source_type="real_api",
            source_url="https://router.project-osrm.org/route/v1/driving",
            is_mock=False
        )

    async def execute(self, latitude: float = 0.0, longitude: float = 0.0, **kwargs: Any) -> list[Evidence]:
        start_lat = latitude if latitude != 0.0 else kwargs.get("start_lat", 0.0)
        start_lon = longitude if longitude != 0.0 else kwargs.get("start_lon", 0.0)
        agent_name = kwargs.get("agent_name", "GeospatialReasoningAgent")
        dest_lat = kwargs.get("dest_lat", start_lat + 0.1)
        dest_lon = kwargs.get("dest_lon", start_lon + 0.1)
        speed_knots = kwargs.get("speed_knots", 10.0)
        now = datetime.utcnow()

        evidence_list: list[Evidence] = []
        timeout = kwargs.get("timeout", 5.0)

        # Calculate straight-line fallback distance & bearing
        geodesic_dist = haversine_distance(start_lat, start_lon, dest_lat, dest_lon)
        dist_km = geodesic_dist["km"]
        bearing_deg = calculate_bearing(start_lat, start_lon, dest_lat, dest_lon)
        eta_hours = calculate_eta(dist_km, speed_knots)

        osrm_url = f"{self.metadata.source_url}/{start_lon},{start_lat};{dest_lon},{dest_lat}"
        params = {"overview": "full", "geometries": "geojson"}

        route_coords = [[start_lat, start_lon], [dest_lat, dest_lon]]
        route_status = "road_network_prototype"
        is_real_route = False
        warnings_list = [
            "PROTOTYPE NOTICE: Path generated via OSRM road-network engine. Marine navigability (bathymetry, sea channels, currents) is NOT verified."
        ]

        try:
            logger.info(f"Querying OSRM prototype route from ({start_lat}, {start_lon}) to ({dest_lat}, {dest_lon})...")
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.get(osrm_url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    routes = data.get("routes", [])
                    if routes:
                        osrm_route = routes[0]
                        geom = osrm_route.get("geometry", {})
                        raw_coords = geom.get("coordinates", [])
                        if raw_coords:
                            # OSRM returns [lon, lat], flip to [lat, lon] for Leaflet
                            route_coords = [[c[1], c[0]] for c in raw_coords]
                            dist_m = osrm_route.get("distance", dist_km * 1000.0)
                            dist_km = round(dist_m / 1000.0, 3)
                            eta_hours = calculate_eta(dist_km, speed_knots)
                            is_real_route = True
                            logger.info(f"OSRM prototype route retrieved: {len(route_coords)} waypoints, {dist_km} km.")

        except Exception as e:
            logger.warning(f"OSRM routing API unavailable ({e}). Falling back to straight-line geodesic calculation.")
            route_status = "unavailable"
            warnings_list.append("ROUTING PROVIDER UNAVAILABLE - Straight line distance calculated only. Not a navigable maritime channel.")

        # 2. Marine Geofence Safety Verification on Route Coordinates
        geospatial_tool = MockGeospatialTool()
        intersected_boundaries = []
        for pt in route_coords:
            lat_p, lon_p = pt[0], pt[1]
            geo_ev = await geospatial_tool.execute(lat_p, lon_p, agent_name=agent_name)
            for ev in geo_ev:
                if ev.parameter == "is_restricted_area" and ev.value is True:
                    b_name = next((e.value for e in geo_ev if e.parameter == "intersecting_boundary_name"), "Protected Marine Zone")
                    if b_name not in intersected_boundaries:
                        intersected_boundaries.append(b_name)

        geofence_verified = True
        if intersected_boundaries:
            route_status = "ROUTE_CONFLICT"
            b_list_str = ", ".join(intersected_boundaries)
            warnings_list.append(f"ROUTE SAFETY CONFLICT: Candidate path intersects geofenced marine zone(s) '{b_list_str}'. Maritime transit prohibited.")

        # Construct Truthful Normalized Payload Objects
        route_payload = {
            "origin": {"lat": start_lat, "lon": start_lon},
            "destination": {"lat": dest_lat, "lon": dest_lon},
            "coordinates": route_coords,
            "distance_km": dist_km,
            "distance_nm": geodesic_dist["nautical_miles"],
            "bearing_degrees": bearing_deg,
            "eta_hours": eta_hours,
            "provider": "OSRM Road Routing API",
            "routing_type": "road_network_prototype",
            "route_calculated": is_real_route,
            "geofence_verified": geofence_verified,
            "marine_navigability_verified": False,
            "status": route_status,
            "warnings": warnings_list,
            "disclaimer": "Prototype routing path generated by OSRM; marine navigability (bathymetry, sea lanes, currents) is NOT verified."
        }

        evidence_list.append(
            Evidence(
                id=f"route_geom_{int(now.timestamp())}",
                source=self.metadata.source_name,
                source_url=self.metadata.source_url,
                source_type=self.metadata.source_type if is_real_route else "derived_calculation",
                parameter="route_geometry",
                value=route_payload,
                unit="geojson_feature",
                location={"lat": start_lat, "lon": start_lon},
                retrieved_at=now,
                valid_from=now,
                valid_until=now + timedelta(hours=12),
                status="observed" if is_real_route else ("unavailable" if route_status == "unavailable" else "derived"),
                confidence=0.70 if is_real_route else 0.50,
                agent=agent_name,
                tool=self.metadata.name
            )
        )

        evidence_list.append(
            Evidence(
                id=f"route_dist_{int(now.timestamp())}",
                source=self.metadata.source_name,
                source_type="derived_calculation",
                parameter="route_distance",
                value=dist_km,
                unit="km",
                location={"lat": start_lat, "lon": start_lon},
                retrieved_at=now,
                status="derived",
                confidence=1.0,
                agent=agent_name,
                tool=self.metadata.name
            )
        )

        evidence_list.append(
            Evidence(
                id=f"route_brg_{int(now.timestamp())}",
                source=self.metadata.source_name,
                source_type="derived_calculation",
                parameter="route_bearing",
                value=bearing_deg,
                unit="degrees",
                location={"lat": start_lat, "lon": start_lon},
                retrieved_at=now,
                status="derived",
                confidence=1.0,
                agent=agent_name,
                tool=self.metadata.name
            )
        )

        evidence_list.append(
            Evidence(
                id=f"route_eta_{int(now.timestamp())}",
                source=self.metadata.source_name,
                source_type="derived_calculation",
                parameter="route_eta",
                value=eta_hours,
                unit="hours",
                location={"lat": start_lat, "lon": start_lon},
                retrieved_at=now,
                status="derived",
                confidence=0.9,
                agent=agent_name,
                tool=self.metadata.name
            )
        )

        return evidence_list
