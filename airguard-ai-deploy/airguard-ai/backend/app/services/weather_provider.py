"""
Weather provider — pulls current conditions from an external API (OpenWeatherMap's
shape by default; any provider returning a compatible JSON body works by
pointing WEATHER_API_BASE_URL at it) over a direct REST call, same pattern
as the SMS/push notification providers: minimal dependency footprint,
testable against a local mock by swapping the base URL, degrades to
"unconfigured" rather than raising when no API key is set.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    temperature: float | None
    humidity: float | None
    wind_speed: float | None
    wind_direction: float | None
    rain_mm: float | None
    pressure_hpa: float | None
    forecast_summary: str | None


class WeatherProvider:
    def is_configured(self) -> bool:
        return bool(settings.WEATHER_API_KEY and settings.WEATHER_SITE_LAT is not None and settings.WEATHER_SITE_LON is not None)

    def fetch_current(self) -> WeatherData | None:
        if not self.is_configured():
            return None

        url = f"{settings.WEATHER_API_BASE_URL}/data/2.5/weather"
        params = {
            "lat": settings.WEATHER_SITE_LAT,
            "lon": settings.WEATHER_SITE_LON,
            "appid": settings.WEATHER_API_KEY,
            "units": "metric",
        }
        try:
            response = httpx.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Weather fetch failed: %s", exc)
            return None

        main = data.get("main", {})
        wind = data.get("wind", {})
        rain = data.get("rain", {})
        weather_list = data.get("weather", [])

        return WeatherData(
            temperature=main.get("temp"),
            humidity=main.get("humidity"),
            wind_speed=wind.get("speed"),
            wind_direction=wind.get("deg"),
            rain_mm=rain.get("1h"),
            pressure_hpa=main.get("pressure"),
            forecast_summary=weather_list[0].get("description") if weather_list else None,
        )


weather_provider = WeatherProvider()
