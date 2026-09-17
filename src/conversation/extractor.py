from __future__ import annotations

import json
import re
from typing import Any

from src.models.schemas import LandProfile


NUMBER = r"(-?\d+(?:\.\d+)?)"

PATTERNS: list[tuple[str, re.Pattern[str], Any]] = [
    ("soil.organic_carbon_pct", re.compile(rf"(?:soc|soil organic carbon|organic carbon)\D{{0,12}}{NUMBER}\s*%?", re.I), float),
    ("soil.ph", re.compile(rf"\bpH\D{{0,8}}{NUMBER}", re.I), float),
    ("climate.rainfall_mm", re.compile(rf"(?:rainfall|precip(?:itation)?)\D{{0,12}}{NUMBER}\s*mm", re.I), float),
    ("biodiversity.native_cover_pct", re.compile(rf"(?:native|forest|habitat)\s+cover\D{{0,8}}{NUMBER}\s*%", re.I), float),
    ("geo.lat", re.compile(rf"\blat(?:itude)?\D{{0,6}}{NUMBER}", re.I), float),
    ("geo.lon", re.compile(rf"\blon(?:gitude)?\D{{0,6}}{NUMBER}", re.I), float),
]

KEYWORD_MAP = {
    "climate.rainfall": {
        "very-wet": ["very wet", "very-wet", "rainforest"],
        "humid": ["humid", "high rainfall", "high rain"],
        "sub-humid": ["sub-humid", "subhumid"],
        "semi-arid": ["semi-arid", "semiarid", "semi arid"],
        "arid": ["arid", "desert"],
        "low": ["rainfall: low", "low rainfall", "low rain", "rainfall low"],
    },
    "soil.moisture": {
        "very_low": ["parched", "very dry soil"],
        "low": ["dry soil", "low moisture"],
        "moderate": ["moderate moisture"],
        "high": ["waterlogged", "high moisture", "wet soil"],
    },
    "climate.temperature": {
        "hot": ["hot", "heatwave", "very warm"],
        "tropical": ["tropical"],
        "subtropical": ["subtropical"],
        "temperate": ["temperate"],
        "cold": ["cold", "boreal", "alpine"],
    },
    "land_use.type": {
        "cropland": ["cropland", "farmland", "field", "crop"],
        "pasture": ["pasture", "rangeland", "grazing land"],
        "forest": ["forest", "woodland"],
        "wetland": ["wetland", "marsh", "peat"],
        "degraded": ["degraded", "bare soil", "wasteland"],
        "mixed": ["mixed farm", "agropastoral"],
        "urban": ["urban", "peri-urban"],
    },
    "land_use.management": {
        "monoculture": ["monoculture", "sole crop", "continuous wheat", "continuous maize"],
        "rotation": ["rotation", "rotational"],
        "agroforestry": ["agroforestry", "parkland"],
        "organic": ["organic"],
        "conventional": ["conventional"],
    },
    "land_use.crop": {
        "wheat": ["wheat"],
        "maize": ["maize", "corn"],
        "rice": ["rice"],
        "soy": ["soy", "soybean"],
        "cotton": ["cotton"],
        "coffee": ["coffee"],
        "cocoa": ["cocoa", "cacao"],
        "pasture grass": ["pasture grass"],
    },
    "land_use.tillage": {
        "conventional": ["plough", "plow", "inversion till"],
        "no-till": ["no-till", "no till", "zero till"],
        "reduced": ["reduced till", "min-till"],
    },
    "human_impact.pesticide_intensity": {
        "high": ["heavy pesticide", "calendar spray", "high pesticide", "insecticide intensive"],
        "moderate": ["some pesticide", "moderate pesticide"],
        "low": ["low pesticide", "organic", "no spray"],
    },
    "human_impact.deforestation": {
        "high": ["deforested", "cleared forest", "recent clearing"],
        "moderate": ["partial clearing", "thinning"],
        "low": ["intact forest"],
    },
    "human_impact.fragmentation": {
        "high": ["fragmented", "isolated patch", "no hedges"],
        "moderate": ["some hedges", "few trees"],
        "low": ["connected habitat", "wildlife corridor"],
    },
    "human_impact.grazing_pressure": {
        "high": ["overgrazed", "continuous grazing", "high stocking"],
        "moderate": ["moderate grazing"],
        "low": ["light grazing", "rested pasture"],
    },
    "biodiversity.species_richness": {
        "very_low": ["no wildlife", "barren", "biodiversity collapsing", "biodiversity is declining"],
        "low": ["low biodiversity", "few species", "declining"],
        "moderate": ["some birds", "moderate diversity"],
        "high": ["species-rich", "high biodiversity"],
    },
    "biodiversity.pollinator_status": {
        "low": ["no bees", "few pollinators", "pollinator decline"],
        "moderate": ["some bees"],
        "high": ["abundant pollinators"],
    },
    "geo.region": {
        "semi-arid": ["semi-arid", "semiarid", "sahel"],
        "arid": ["arid region", "dryland"],
        "tropical": ["tropics", "tropical"],
        "temperate": ["temperate region"],
        "mediterranean": ["mediterranean"],
    },
}

RAINFALL_NORMALIZE = {
    "low": "semi-arid",
    "dry": "semi-arid",
    "high": "humid",
}


def _set_path(profile: LandProfile, path: str, value: Any) -> None:
    group, key = path.split(".", 1)
    target = getattr(profile, group)
    setattr(target, key, value)


def _get_path(profile: LandProfile, path: str) -> Any:
    group, key = path.split(".", 1)
    return getattr(getattr(profile, group), key)


def merge_profiles(base: LandProfile, incoming: LandProfile | None) -> LandProfile:
    if incoming is None:
        return base
    merged = base.model_copy(deep=True)
    for group in ("soil", "climate", "land_use", "biodiversity", "human_impact", "geo"):
        current = getattr(merged, group)
        overlay = getattr(incoming, group).model_dump(exclude_none=True)
        for key, value in overlay.items():
            setattr(current, key, value)
    if incoming.notes:
        merged.notes.extend(incoming.notes)
    return merged


def extract_from_text(text: str, profile: LandProfile) -> LandProfile:
    profile = profile.model_copy(deep=True)
    blob = text.strip()
    if not blob:
        return profile

    json_match = re.search(r"\{[\s\S]+\}", blob)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            incoming = LandProfile.model_validate(_coerce_json(parsed))
            profile = merge_profiles(profile, incoming)
        except Exception:
            pass

    for path, pattern, caster in PATTERNS:
        match = pattern.search(blob)
        if match and _get_path(profile, path) is None:
            try:
                _set_path(profile, path, caster(match.group(1)))
            except ValueError:
                continue

    lowered = blob.lower()
    for path, mapping in KEYWORD_MAP.items():
        if _get_path(profile, path) is not None:
            continue
        # prefer longer phrases
        for value, phrases in mapping.items():
            if any(phrase in lowered for phrase in phrases):
                _set_path(profile, path, value)
                break

    rainfall = profile.climate.rainfall
    if rainfall in RAINFALL_NORMALIZE:
        profile.climate.rainfall = RAINFALL_NORMALIZE[rainfall]

    if profile.land_use.crop and not profile.land_use.type:
        profile.land_use.type = "cropland"
    if profile.land_use.management == "monoculture" and not profile.land_use.type:
        profile.land_use.type = "cropland"
    if profile.geo.region and not profile.climate.rainfall:
        if "semi-arid" in profile.geo.region:
            profile.climate.rainfall = "semi-arid"
        elif profile.geo.region == "arid":
            profile.climate.rainfall = "arid"

    if "biodiversity" in lowered and "declin" in lowered:
        profile.biodiversity.species_richness = profile.biodiversity.species_richness or "low"
        profile.notes.append("User reports biodiversity decline.")

    return profile


def _coerce_json(payload: dict) -> dict:
    """Accept both nested LandProfile JSON and flat keys from the brief."""
    if any(key in payload for key in ("soil", "climate", "land_use")):
        return payload
    aliases = {
        "soil_organic_carbon": ("soil", "organic_carbon_pct"),
        "soc": ("soil", "organic_carbon_pct"),
        "organic_carbon": ("soil", "organic_carbon_pct"),
        "ph": ("soil", "ph"),
        "rainfall": ("climate", "rainfall"),
        "rainfall_mm": ("climate", "rainfall_mm"),
        "crop": ("land_use", "crop"),
        "land_use": ("land_use", "type"),
        "region": ("geo", "region"),
        "lat": ("geo", "lat"),
        "lon": ("geo", "lon"),
        "latitude": ("geo", "lat"),
        "longitude": ("geo", "lon"),
        "species_richness": ("biodiversity", "species_richness"),
        "pesticides": ("human_impact", "pesticide_intensity"),
        "deforestation": ("human_impact", "deforestation"),
    }
    nested: dict[str, dict] = {}
    for key, value in payload.items():
        path = aliases.get(key.lower().replace(" ", "_"))
        if not path:
            continue
        group, field = path
        nested.setdefault(group, {})[field] = value
    if nested.get("land_use", {}).get("crop") and "type" not in nested.get("land_use", {}):
        nested["land_use"]["type"] = "cropland"
    if nested.get("land_use", {}).get("crop") and "monoculture" in str(nested["land_use"].get("crop", "")).lower():
        nested["land_use"]["management"] = "monoculture"
        crop = re.sub(r"monoculture", "", str(nested["land_use"]["crop"]), flags=re.I).strip()
        nested["land_use"]["crop"] = crop or nested["land_use"]["crop"]
    rainfall = nested.get("climate", {}).get("rainfall")
    if isinstance(rainfall, str) and rainfall.lower() in RAINFALL_NORMALIZE:
        nested["climate"]["rainfall"] = RAINFALL_NORMALIZE[rainfall.lower()]
    return nested
