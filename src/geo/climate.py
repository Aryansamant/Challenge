from __future__ import annotations

import httpx

from src.config import settings
from src.models.schemas import Climate, LandProfile


LAT_BANDS = [
    (10, "tropical"),
    (23.5, "subtropical"),
    (40, "temperate"),
    (60, "boreal"),
    (90, "polar"),
]


def lat_band(lat: float) -> str:
    abs_lat = abs(lat)
    for limit, name in LAT_BANDS:
        if abs_lat <= limit:
            return name
    return "polar"


def rainfall_class(mm: float) -> str:
    if mm < 250:
        return "arid"
    if mm < 500:
        return "semi-arid"
    if mm < 1000:
        return "sub-humid"
    if mm < 2000:
        return "humid"
    return "very-wet"


def enrich_from_coordinates(profile: LandProfile) -> LandProfile:
    if profile.geo.lat is None or profile.geo.lon is None:
        return profile
    profile = profile.model_copy(deep=True)
    band = lat_band(profile.geo.lat)
    profile.climate.climate_zone = profile.climate.climate_zone or band
    profile.geo.region = profile.geo.region or band

    if not settings.enable_geo_climate:
        return profile

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": profile.geo.lat,
        "longitude": profile.geo.lon,
        "start_date": "2020-01-01",
        "end_date": "2023-12-31",
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "UTC",
    }
    try:
        with httpx.Client(timeout=6.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            daily = response.json().get("daily", {})
        temps = [t for t in daily.get("temperature_2m_mean", []) if t is not None]
        rains = [r for r in daily.get("precipitation_sum", []) if r is not None]
        if temps:
            profile.climate.mean_temp_c = round(sum(temps) / len(temps), 2)
            if profile.climate.mean_temp_c >= 25:
                profile.climate.temperature = profile.climate.temperature or "hot"
            elif profile.climate.mean_temp_c >= 18:
                profile.climate.temperature = profile.climate.temperature or "tropical"
            elif profile.climate.mean_temp_c >= 10:
                profile.climate.temperature = profile.climate.temperature or "temperate"
            else:
                profile.climate.temperature = profile.climate.temperature or "cold"
        if rains:
            # Open-Meteo daily precip summed over 4 years of days → mean annual
            years = 4.0
            annual = sum(rains) / years
            profile.climate.rainfall_mm = round(annual, 1)
            profile.climate.rainfall = profile.climate.rainfall or rainfall_class(annual)
            profile.climate.drought_risk = "high" if annual < 500 else "moderate" if annual < 900 else "low"
        profile.notes.append("Climate normals inferred from Open-Meteo 2020–2023 daily archive.")
    except Exception:
        profile.notes.append(
            f"Open-Meteo lookup failed; using latitude band '{band}' only. Rainfall still needs a user estimate."
        )
    return profile


def merge_climate(base: Climate, overlay: Climate) -> Climate:
    data = base.model_dump()
    for key, value in overlay.model_dump(exclude_none=True).items():
        data[key] = value
    return Climate.model_validate(data)
