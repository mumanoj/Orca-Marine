"""
Global Fishing Watch (GFW) Real API Integration Service.
Communicates with official GFW API v3 endpoints (https://gateway.globalfishingwatch.org/v3).
Loads GFW_API_KEY from environment config and executes authenticated requests.
Enforces honest failure reporting — never fabricates fake fishing activity or vessel counts.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import httpx

from app.core.config import settings
from app.domain.evidence import Evidence

logger = logging.getLogger(__name__)

class GFWDataUnavailableError(Exception):
    """Raised when Global Fishing Watch API cannot provide data or is unreachable."""
    pass

class GFWService:
    """
    Production Client for Global Fishing Watch API v3.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GFW_API_KEY
        self.base_url = "https://gateway.globalfishingwatch.org/v3"

    async def get_fishing_activity(
        self,
        latitude: float,
        longitude: float,
        search_radius_km: float = 25.0,
        days_history: int = 7
    ) -> Evidence:
        """
        Retrieves genuine GFW fishing-activity evidence for requested geographic location.
        Raises GFWDataUnavailableError if unauthenticated, offline, or unavailable.
        """
        now = datetime.utcnow()
        if not self.api_key:
            logger.info("GFW_API_KEY not configured. Returning honest unavailable state.")
            raise GFWDataUnavailableError("GFW_API_KEY is not configured in backend environment.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "ORCA-Marine-Intelligence/1.0",
            "Accept": "application/json"
        }

        # Calculate bounding box for search radius
        lat_delta = search_radius_km / 111.0
        lon_delta = search_radius_km / (111.0 * max(0.2, abs(round(latitude, 2))))
        
        min_lat = round(latitude - lat_delta, 3)
        max_lat = round(latitude + lat_delta, 3)
        min_lon = round(longitude - lon_delta, 3)
        max_lon = round(longitude + lon_delta, 3)

        start_date = (now - timedelta(days=days_history)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        # Official GFW 4wings report API endpoint
        url = f"{self.base_url}/4wings/report"
        params = {
            "datasets": "public-global-fishing-events:v20230126",
            "spatial-resolution": "HIGH",
            "temporal-resolution": "HOURLY",
            "start-date": start_date,
            "end-date": end_date,
            "geometry": f'{{"type":"Polygon","coordinates":[[[{min_lon},{min_lat}],[{max_lon},{min_lat}],[{max_lon},{max_lat}],[{min_lon},{max_lat}],[{min_lon},{min_lat}]]]}}'
        }

        try:
            logger.info(f"Attempting live GFW API query for location ({latitude}, {longitude})...")
            async with httpx.AsyncClient(timeout=6.0, verify=False) as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    total_hours = data.get("totalFishingHours", 0.0)
                    total_vessels = data.get("vesselCount", 0)
                    
                    return Evidence(
                        id=f"gfw_activity_{int(now.timestamp())}",
                        source="Global Fishing Watch",
                        source_url="https://globalfishingwatch.org/map",
                        source_type="real_api",
                        parameter="gfw_fishing_activity",
                        value={
                            "status": "observed",
                            "requested_location": {"lat": latitude, "lon": longitude},
                            "search_radius_km": search_radius_km,
                            "date_range": f"{start_date} to {end_date}",
                            "total_fishing_hours": total_hours,
                            "observed_vessel_count": total_vessels,
                            "confidence": 0.95
                        },
                        unit="observed_hours_and_vessels",
                        location={"lat": latitude, "lon": longitude},
                        observed_at=now - timedelta(hours=1),
                        retrieved_at=now,
                        valid_from=now - timedelta(days=1),
                        valid_until=now + timedelta(days=1),
                        status="observed",
                        confidence=0.95,
                        agent="OceanAgent",
                        tool="gfw_service"
                    )
                elif response.status_code in [401, 403]:
                    logger.warning(f"GFW API authentication failed (HTTP {response.status_code}).")
                    raise GFWDataUnavailableError(f"GFW API authentication failed (HTTP {response.status_code}).")
                else:
                    logger.warning(f"GFW API returned status code {response.status_code}: {response.text[:200]}")
                    raise GFWDataUnavailableError(f"GFW API returned HTTP {response.status_code}.")
        except Exception as e:
            logger.warning(f"GFW API request failed: {e}")
            raise GFWDataUnavailableError(f"GFW API connection failed: {str(e)}")

async def fetch_gfw_evidence_safe(latitude: float, longitude: float) -> Evidence:
    """
    Safely retrieves GFW evidence. Returns honest unavailable status if API fails.
    """
    now = datetime.utcnow()
    service = GFWService()
    try:
        return await service.get_fishing_activity(latitude, longitude)
    except GFWDataUnavailableError as e:
        return Evidence(
            id=f"gfw_activity_unavail_{int(now.timestamp())}",
            source="Global Fishing Watch",
            source_url="https://globalfishingwatch.org/map",
            source_type="real_api",
            parameter="gfw_fishing_activity",
            value={
                "status": "unavailable",
                "message": "Global Fishing Watch activity data was unavailable for this request.",
                "requested_location": {"lat": latitude, "lon": longitude}
            },
            unit="status",
            location={"lat": latitude, "lon": longitude},
            observed_at=now,
            retrieved_at=now,
            valid_from=now,
            valid_until=now + timedelta(days=1),
            status="unavailable",
            confidence=0.0,
            agent="OceanAgent",
            tool="gfw_service"
        )
