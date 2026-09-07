import logging
from datetime import datetime, timedelta
from typing import Any
import httpx

from app.core.config import settings
from app.domain.evidence import Evidence
from app.tools.registry import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)

class RealAdvisoryTool(BaseTool):
    """
    Production Real Advisory Tool Adapter.
    Checks Open-Meteo severe weather codes and wind parameters while reporting 
    official IMD / INCOIS advisory feed availability as 'unavailable'.
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="marine_advisory_tool",
            description="Checks model-derived severe weather codes from Open-Meteo and reports official marine advisory status.",
            source_name="Open-Meteo Weather API",
            source_type="real_api",
            source_url="https://api.open-meteo.com/v1/forecast",
            is_mock=False
        )

    async def execute(self, latitude: float, longitude: float, **kwargs: Any) -> list[Evidence]:
        agent_name = kwargs.get("agent_name", "MarineAdvisoryAgent")
        now = datetime.utcnow()
        warning_active = kwargs.get("warning_active", False)
        
        evidence_list: list[Evidence] = []

        # 1. Official IMD / INCOIS Direct Advisory Availability Check
        evidence_list.append(
            Evidence(
                id=f"adv_official_status_{int(now.timestamp())}",
                source="IMD / INCOIS Coastal Advisory Feed",
                source_url="https://incois.gov.in/portal/advisory",
                source_type="real_api",
                parameter="official_marine_advisory",
                value="Official IMD / INCOIS advisory feed unavailable without direct MoES API credentials.",
                unit="string",
                location={"lat": latitude, "lon": longitude},
                retrieved_at=now,
                status="unavailable",
                confidence=0.0,
                agent=agent_name,
                tool=self.metadata.name
            )
        )

        # 2. Open-Meteo Modelled Severe Weather Code Check
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "weather_code,wind_speed_10m",
            "forecast_days": 1
        }
        timeout = kwargs.get("timeout", 5.0)

        try:
            logger.info(f"Querying Open-Meteo severe weather parameters for coordinate ({latitude}, {longitude})...")
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(self.metadata.source_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    current_data = data.get("current", {})
                    wcode = current_data.get("weather_code", 0)
                    wind_speed = current_data.get("wind_speed_10m", 0.0)
                    
                    # WMO 95-99 = Severe Thunderstorm/Gale
                    if wcode in [95, 96, 99] or wind_speed > 50.0 or warning_active:
                        warning_active = True
                        warning_desc = f"Modelled Severe Weather Condition: Wind Speed ({wind_speed} km/h) & WMO Weather Code {wcode} indicate gale/storm hazards."
                    else:
                        warning_desc = "No severe weather codes detected in current Open-Meteo forecast model."
                        
                    evidence_list.append(
                        Evidence(
                            id=f"adv_curr_alert_{int(now.timestamp())}",
                            source=self.metadata.source_name,
                            source_url=self.metadata.source_url,
                            source_type=self.metadata.source_type,
                            parameter="active_warning",
                            value=warning_active,
                            unit="boolean",
                            location={"lat": latitude, "lon": longitude},
                            observed_at=now,
                            retrieved_at=now,
                            valid_from=now,
                            valid_until=now + timedelta(hours=6),
                            status="forecast",
                            confidence=0.85,
                            agent=agent_name,
                            tool=self.metadata.name
                        )
                    )

                    evidence_list.append(
                        Evidence(
                            id=f"adv_curr_text_{int(now.timestamp())}",
                            source=self.metadata.source_name,
                            source_url=self.metadata.source_url,
                            source_type=self.metadata.source_type,
                            parameter="warning_details",
                            value=warning_desc,
                            unit="string",
                            location={"lat": latitude, "lon": longitude},
                            observed_at=now,
                            retrieved_at=now,
                            valid_from=now,
                            valid_until=now + timedelta(hours=6),
                            status="forecast",
                            confidence=0.85,
                            agent=agent_name,
                            tool=self.metadata.name
                        )
                    )
                    return evidence_list

        except (httpx.TimeoutException, httpx.HTTPStatusError, Exception) as e:
            logger.error(f"Open-Meteo API query failed: {e}. Returning degraded advisory evidence.")
            evidence_list.append(
                Evidence(
                    id=f"adv_degraded_{int(now.timestamp())}",
                    source=self.metadata.source_name,
                    source_url=self.metadata.source_url,
                    source_type=self.metadata.source_type,
                    parameter="active_warning",
                    value=True,  # Safety-first fallback assumption when weather API is down
                    unit="boolean",
                    location={"lat": latitude, "lon": longitude},
                    retrieved_at=now,
                    status="unavailable",
                    confidence=0.5,
                    agent=agent_name,
                    tool=self.metadata.name
                )
            )

        return evidence_list
