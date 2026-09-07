import logging
from datetime import datetime, timedelta
from typing import Any, Optional
import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.domain.evidence import Evidence
from app.tools.registry import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)

# WMO Weather Code interpretation dictionary
WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

class RealWeatherTool(BaseTool):
    """
    Production Real Weather Adapter using Open-Meteo API.
    Retrieves real-time current weather observations and hourly forecasts.
    Converts API payloads into provenance-rich ORCA Evidence models.
    """
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="weather_intelligence_tool",
            description="Retrieves live current weather observations and hourly forecasts from Open-Meteo Weather API.",
            source_name="Open-Meteo Weather API",
            source_type="real_api",
            source_url=settings.WEATHER_API_BASE_URL,
            is_mock=False
        )

    async def execute(self, latitude: float, longitude: float, **kwargs: Any) -> list[Evidence]:
        agent_name = kwargs.get("agent_name", "WeatherAgent")
        now = datetime.utcnow()
        
        temp_reqs = kwargs.get("temporal_requirements", {})
        forecast_days = 2 if (temp_reqs.get("is_future_forecast") or temp_reqs.get("time_frame") in ["tomorrow", "tomorrow_morning"]) else 1
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
            "hourly": "temperature_2m,precipitation_probability,wind_speed_10m",
            "forecast_days": forecast_days,
            "wind_speed_unit": "kmh"
        }
        
        timeout = kwargs.get("timeout", 5.0)

        try:
            logger.info(f"Querying Open-Meteo Weather API for location ({latitude}, {longitude})...")
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(self.metadata.source_url, params=params)
                response.raise_for_status()
                data = response.json()

            evidence_list: list[Evidence] = []
            
            # 1. Parse CURRENT OBSERVATIONS (status = 'observed')
            current_data = data.get("current", {})
            current_time_str = current_data.get("time")
            observed_at = datetime.fromisoformat(current_time_str) if current_time_str else now

            # Temperature
            if "temperature_2m" in current_data:
                evidence_list.append(
                    Evidence(
                        id=f"wea_curr_temp_{int(now.timestamp())}",
                        source=self.metadata.source_name,
                        source_url=self.metadata.source_url,
                        source_type=self.metadata.source_type,
                        parameter="temperature",
                        value=float(current_data["temperature_2m"]),
                        unit="C",
                        location={"lat": latitude, "lon": longitude},
                        observed_at=observed_at,
                        retrieved_at=now,
                        valid_from=now,
                        valid_until=now + timedelta(hours=1),
                        status="observed",
                        confidence=1.0,
                        agent=agent_name,
                        tool=self.metadata.name
                    )
                )

            # Wind Speed
            if "wind_speed_10m" in current_data:
                evidence_list.append(
                    Evidence(
                        id=f"wea_curr_wind_{int(now.timestamp())}",
                        source=self.metadata.source_name,
                        source_url=self.metadata.source_url,
                        source_type=self.metadata.source_type,
                        parameter="wind_speed",
                        value=float(current_data["wind_speed_10m"]),
                        unit="km/h",
                        location={"lat": latitude, "lon": longitude},
                        observed_at=observed_at,
                        retrieved_at=now,
                        valid_from=now,
                        valid_until=now + timedelta(hours=1),
                        status="observed",
                        confidence=1.0,
                        agent=agent_name,
                        tool=self.metadata.name
                    )
                )

            # Wind Direction
            if "wind_direction_10m" in current_data:
                evidence_list.append(
                    Evidence(
                        id=f"wea_curr_winddir_{int(now.timestamp())}",
                        source=self.metadata.source_name,
                        source_url=self.metadata.source_url,
                        source_type=self.metadata.source_type,
                        parameter="wind_direction",
                        value=float(current_data["wind_direction_10m"]),
                        unit="deg",
                        location={"lat": latitude, "lon": longitude},
                        observed_at=observed_at,
                        retrieved_at=now,
                        valid_from=now,
                        valid_until=now + timedelta(hours=1),
                        status="observed",
                        confidence=1.0,
                        agent=agent_name,
                        tool=self.metadata.name
                    )
                )

            # Precipitation
            if "precipitation" in current_data:
                evidence_list.append(
                    Evidence(
                        id=f"wea_curr_precip_{int(now.timestamp())}",
                        source=self.metadata.source_name,
                        source_url=self.metadata.source_url,
                        source_type=self.metadata.source_type,
                        parameter="precipitation",
                        value=float(current_data["precipitation"]),
                        unit="mm",
                        location={"lat": latitude, "lon": longitude},
                        observed_at=observed_at,
                        retrieved_at=now,
                        valid_from=now,
                        valid_until=now + timedelta(hours=1),
                        status="observed",
                        confidence=1.0,
                        agent=agent_name,
                        tool=self.metadata.name
                    )
                )

            # Weather Code (severe weather indicators)
            if "weather_code" in current_data:
                wcode = int(current_data["weather_code"])
                wdesc = WMO_WEATHER_CODES.get(wcode, "Unknown weather state")
                evidence_list.append(
                    Evidence(
                        id=f"wea_curr_wcode_{int(now.timestamp())}",
                        source=self.metadata.source_name,
                        source_url=self.metadata.source_url,
                        source_type=self.metadata.source_type,
                        parameter="weather_condition",
                        value=wdesc,
                        unit="string",
                        location={"lat": latitude, "lon": longitude},
                        observed_at=observed_at,
                        retrieved_at=now,
                        valid_from=now,
                        valid_until=now + timedelta(hours=1),
                        status="observed",
                        confidence=1.0,
                        agent=agent_name,
                        tool=self.metadata.name
                    )
                )

            # 2. Parse HOURLY FORECASTS (status = 'forecast')
            hourly_data = data.get("hourly", {})
            if "precipitation_probability" in hourly_data and len(hourly_data["precipitation_probability"]) > 0:
                forecast_precip_prob = float(hourly_data["precipitation_probability"][0])
                evidence_list.append(
                    Evidence(
                        id=f"wea_fcst_precip_prob_{int(now.timestamp())}",
                        source=self.metadata.source_name,
                        source_url=self.metadata.source_url,
                        source_type=self.metadata.source_type,
                        parameter="precipitation_probability",
                        value=forecast_precip_prob,
                        unit="%",
                        location={"lat": latitude, "lon": longitude},
                        observed_at=observed_at,
                        retrieved_at=now,
                        valid_from=now,
                        valid_until=now + timedelta(hours=12),
                        status="forecast",
                        confidence=0.9,
                        agent=agent_name,
                        tool=self.metadata.name
                    )
                )

            # 3. Parse Tomorrow Forecast Period Evidence if requested
            temp_reqs = kwargs.get("temporal_requirements", {})
            if temp_reqs.get("is_future_forecast") or temp_reqs.get("time_frame") in ["tomorrow", "tomorrow_morning", "tonight"] or "tonight" in str(temp_reqs.get("time_frame")):
                hourly_precip = hourly_data.get("precipitation_probability", [])
                hourly_temp = hourly_data.get("temperature_2m", [])
                hourly_wind = hourly_data.get("wind_speed_10m", [])
                
                period_label = temp_reqs.get("target_period", "Tomorrow Morning (06:00 - 12:00 IST)")
                target_h = temp_reqs.get("target_hour")
                
                if target_h is not None and len(hourly_temp) > 0:
                    current_h = now.hour
                    hours_ahead = (target_h - current_h) % 24
                    if hours_ahead == 0:
                        hours_ahead = 24
                    tm_idx = hours_ahead if len(hourly_temp) > hours_ahead else (len(hourly_temp) - 1)
                else:
                    tm_idx = 24 if len(hourly_temp) > 24 else (len(hourly_temp) - 1 if len(hourly_temp) > 0 else None)

                if tm_idx is not None:
                    evidence_list.append(
                        Evidence(
                            id=f"wea_fcst_period_label_{int(now.timestamp())}",
                            source=self.metadata.source_name,
                            source_type=self.metadata.source_type,
                            parameter="forecast_period_label",
                            value=period_label,
                            unit="string",
                            location={"lat": latitude, "lon": longitude},
                            retrieved_at=now,
                            status="forecast",
                            confidence=0.95,
                            agent=agent_name,
                            tool=self.metadata.name
                        )
                    )
                    if len(hourly_temp) > tm_idx:
                        evidence_list.append(
                            Evidence(
                                id=f"wea_fcst_tm_temp_{int(now.timestamp())}",
                                source=self.metadata.source_name,
                                source_type=self.metadata.source_type,
                                parameter="forecast_temperature",
                                value=float(hourly_temp[tm_idx]),
                                unit="C",
                                location={"lat": latitude, "lon": longitude},
                                retrieved_at=now,
                                status="forecast",
                                confidence=0.9,
                                agent=agent_name,
                                tool=self.metadata.name
                            )
                        )
                    if len(hourly_wind) > tm_idx:
                        evidence_list.append(
                            Evidence(
                                id=f"wea_fcst_tm_wind_{int(now.timestamp())}",
                                source=self.metadata.source_name,
                                source_type=self.metadata.source_type,
                                parameter="forecast_wind_speed",
                                value=float(hourly_wind[tm_idx]),
                                unit="km/h",
                                location={"lat": latitude, "lon": longitude},
                                retrieved_at=now,
                                status="forecast",
                                confidence=0.9,
                                agent=agent_name,
                                tool=self.metadata.name
                            )
                        )

            return evidence_list

        except (httpx.TimeoutException, httpx.HTTPStatusError, Exception) as e:
            logger.error(f"Open-Meteo Weather API request failed: {e}")
            raise RuntimeError(f"Real weather API retrieval failed: {str(e)}")
