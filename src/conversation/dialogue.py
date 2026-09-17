from __future__ import annotations

from src.models.schemas import FollowUpQuestion, LandProfile

PRIORITY_SLOTS: list[FollowUpQuestion] = [
    FollowUpQuestion(
        slot="soil.organic_carbon_pct",
        question="Can you provide soil organic carbon % (topsoil SOC, or organic matter % ÷ 1.72)?",
        why_needed="SOC is the energy base of soil food webs and a proxy for water-holding capacity.",
    ),
    FollowUpQuestion(
        slot="climate.rainfall",
        question="What is the rainfall pattern — arid, semi-arid, sub-humid, or humid, and is it short storms or a long wet season?",
        why_needed="In drylands, water — not fertilizer — is usually the binding constraint on species survival.",
    ),
    FollowUpQuestion(
        slot="land_use.management",
        question="What is the land use type: monoculture crop (which crop?), mixed rotation, pasture, forest, or degraded bare ground?",
        why_needed="Land-use architecture sets habitat complexity independently of soil tests.",
    ),
    FollowUpQuestion(
        slot="soil.ph",
        question="Do you have a soil pH value?",
        why_needed="pH is the strongest continental predictor of soil bacterial diversity.",
    ),
    FollowUpQuestion(
        slot="human_impact.pesticide_intensity",
        question="How intense is pesticide or insecticide use (low / moderate / high / unknown)?",
        why_needed="Chemical pressure can cancel habitat restorations by turning floral strips into ecological traps.",
    ),
    FollowUpQuestion(
        slot="geo.lat",
        question="If you can, share latitude and longitude so climate normals can be inferred.",
        why_needed="Coordinates let the engine pull rainfall and temperature context instead of guessing the biome.",
    ),
]


def _filled(profile: LandProfile, slot: str) -> bool:
    group, key = slot.split(".", 1)
    value = getattr(getattr(profile, group), key)
    return value is not None and value != ""


def needed_questions(profile: LandProfile, limit: int = 3) -> list[FollowUpQuestion]:
    missing = [item for item in PRIORITY_SLOTS if not _filled(profile, item.slot)]
    # rainfall can be inferred from region
    filtered = []
    for item in missing:
        if item.slot == "climate.rainfall" and (profile.geo.region or profile.climate.rainfall_mm):
            continue
        if item.slot == "geo.lat" and profile.geo.region:
            continue
        filtered.append(item)
    return filtered[:limit]


def ready_to_recommend(profile: LandProfile) -> bool:
    """Need at least three environmental variables spanning soil, climate/water, and land use/habitat."""
    axes = [
        any(
            [
                profile.soil.organic_carbon_pct is not None,
                profile.soil.ph is not None,
                profile.soil.moisture,
                profile.soil.texture,
            ]
        ),
        any(
            [
                profile.climate.rainfall,
                profile.climate.rainfall_mm is not None,
                profile.climate.temperature,
                profile.geo.region,
                profile.geo.lat is not None,
            ]
        ),
        any(
            [
                profile.land_use.type,
                profile.land_use.crop,
                profile.land_use.management,
                profile.biodiversity.native_cover_pct is not None,
                profile.human_impact.deforestation,
                profile.human_impact.fragmentation,
            ]
        ),
    ]
    return sum(1 for axis in axes if axis) >= 3 or profile.filled_variable_count() >= 4
