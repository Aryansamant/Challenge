from __future__ import annotations

from src.knowledge.store import thresholds
from src.models.schemas import LandProfile, MetricStatus

RAINFALL_SEVERITY = {
    "arid": "critical",
    "semi-arid": "poor",
    "sub-humid": "moderate",
    "humid": "adequate",
    "very-wet": "adequate",
}


def _climate_key(profile: LandProfile) -> str:
    rainfall = (profile.climate.rainfall or "").lower()
    if rainfall in {"arid", "semi-arid", "sub-humid", "humid"}:
        return rainfall
    region = (profile.geo.region or profile.climate.climate_zone or "").lower()
    if "semi-arid" in region or "semiarid" in region:
        return "semi-arid"
    if "arid" in region:
        return "arid"
    return "default"


def diagnose(profile: LandProfile) -> list[MetricStatus]:
    cfg = thresholds()
    climate = _climate_key(profile)
    status: list[MetricStatus] = []

    soc = profile.soil.organic_carbon_pct
    bands = cfg["soil_organic_carbon_pct"]["context_adjustments"].get(
        climate, cfg["soil_organic_carbon_pct"]["context_adjustments"]["default"]
    )
    if soc is not None:
        if soc < bands["critical"]:
            sev = "critical"
            why = (
                f"SOC {soc}% is below the {climate} critical threshold of {bands['critical']}%. "
                "Microbial habitat and available water capacity are both severely constrained."
            )
        elif soc < bands["poor"]:
            sev = "poor"
            why = f"SOC {soc}% is low for {climate} cropland; soil food webs and aggregation will be weak."
        elif soc < bands["moderate"]:
            sev = "moderate"
            why = f"SOC {soc}% is intermediate; further gains still buy drought buffering and biodiversity."
        else:
            sev = "adequate"
            why = f"SOC {soc}% is relatively adequate for {climate} systems; protect it rather than mining it."
        status.append(
            MetricStatus(
                metric="soil organic carbon",
                value=f"{soc}%",
                severity=sev,
                rationale=why,
                linked_metrics=["microbial diversity", "soil moisture", "erosion"],
            )
        )

    ph = profile.soil.ph
    if ph is not None:
        if ph < 5.0:
            sev, why = "critical", f"pH {ph} is strongly acidic; Al toxicity and collapsed bacterial richness are likely."
        elif ph < 5.5:
            sev, why = "poor", f"pH {ph} is acidic enough to impair P availability, rhizobia and many crops."
        elif ph > 8.8:
            sev, why = "critical", f"pH {ph} is extremely alkaline; micronutrient lock-up will filter plant and microbial guilds."
        elif ph > 8.3:
            sev, why = "poor", f"pH {ph} is alkaline; expect Fe/Zn/P constraints unless gypsum/organic matter are used."
        elif 6.0 <= ph <= 7.5:
            sev, why = "adequate", f"pH {ph} sits in the band where bacterial diversity typically peaks."
        else:
            sev, why = "moderate", f"pH {ph} is usable but not optimal for microbial richness."
        status.append(
            MetricStatus(
                metric="soil pH",
                value=str(ph),
                severity=sev,
                rationale=why,
                linked_metrics=["microbial diversity", "nutrient cycling"],
            )
        )

    rainfall = (profile.climate.rainfall or "").lower()
    if rainfall:
        sev = RAINFALL_SEVERITY.get(rainfall, "unknown")
        moisture = profile.soil.moisture or "not provided"
        status.append(
            MetricStatus(
                metric="rainfall / moisture regime",
                value=f"{rainfall}; soil moisture={moisture}",
                severity=sev if rainfall in RAINFALL_SEVERITY else "unknown",
                rationale=(
                    f"A {rainfall} regime makes infiltration, residue cover and perennial structure first-order "
                    "biodiversity controls rather than optional extras."
                    if rainfall in {"arid", "semi-arid"}
                    else f"Rainfall class '{rainfall}' still interacts with SOC and land use to set habitat energy."
                ),
                linked_metrics=["soil moisture", "species richness", "soil organic carbon"],
            )
        )

    management = (profile.land_use.management or "").lower()
    crop = (profile.land_use.crop or profile.land_use.type or "").lower()
    if management or crop:
        monoculture = "monoculture" in management or "monoculture" in crop
        sev = "poor" if monoculture else "moderate"
        if "forest" in (profile.land_use.type or "") and not monoculture:
            sev = "adequate"
        status.append(
            MetricStatus(
                metric="land use / habitat simplification",
                value=f"{profile.land_use.type or 'unknown type'}; {management or 'unspecified'} {profile.land_use.crop or ''}".strip(),
                severity=sev,
                rationale=(
                    "Monoculture filters habitat to a single plant architecture and a short floral calendar, "
                    "collapsing associated insect and bird richness even if yields are stable."
                    if monoculture
                    else "Land use still sets the habitat template; diversification and margins determine remaining richness."
                ),
                linked_metrics=["plant diversity", "pollinators", "species richness"],
            )
        )

    if profile.human_impact.fragmentation or profile.human_impact.deforestation:
        frag = (profile.human_impact.fragmentation or profile.human_impact.deforestation or "").lower()
        sev = "critical" if frag == "high" else "poor" if frag == "moderate" else "moderate"
        status.append(
            MetricStatus(
                metric="fragmentation / deforestation",
                value=frag,
                severity=sev,
                rationale="Isolation and edge drying remove area-sensitive species and accelerate SOC loss at forest edges.",
                linked_metrics=["species richness", "microclimate", "soil organic carbon"],
            )
        )

    if profile.human_impact.pesticide_intensity:
        level = profile.human_impact.pesticide_intensity.lower()
        sev = "critical" if level == "high" else "poor" if level == "moderate" else "moderate"
        status.append(
            MetricStatus(
                metric="pesticide pressure",
                value=level,
                severity=sev,
                rationale="Non-target insect and soil-fauna exposure can cancel habitat investments if spraying stays calendar-based.",
                linked_metrics=["pollinators", "microbial diversity"],
            )
        )

    native = profile.biodiversity.native_cover_pct
    if native is not None:
        if native < 10:
            sev = "critical"
        elif native < 20:
            sev = "poor"
        elif native < 40:
            sev = "moderate"
        else:
            sev = "adequate"
        status.append(
            MetricStatus(
                metric="native / semi-natural cover",
                value=f"{native}%",
                severity=sev,
                rationale="Pollination and dispersal often collapse below ~10–20% semi-natural cover in the mosaic.",
                linked_metrics=["pollinators", "species richness", "fragmentation"],
            )
        )

    if profile.biodiversity.species_richness:
        mapping = {"very_low": "critical", "low": "poor", "moderate": "moderate", "high": "adequate"}
        sev = mapping.get(profile.biodiversity.species_richness, "unknown")
        status.append(
            MetricStatus(
                metric="species richness",
                value=profile.biodiversity.species_richness,
                severity=sev,
                rationale="Reported richness is treated as an outcome of soil, water and habitat filters, not an isolated score.",
                linked_metrics=["habitat heterogeneity", "soil organic carbon", "rainfall"],
            )
        )

    return status


def limiting_factors(status: list[MetricStatus]) -> list[str]:
    rank = {"critical": 0, "poor": 1, "moderate": 2, "adequate": 3, "unknown": 4}
    ordered = sorted(status, key=lambda item: rank.get(item.severity, 9))
    return [item.metric for item in ordered if item.severity in {"critical", "poor"}][:4]


def overall_confidence(profile: LandProfile, status: list[MetricStatus]) -> str:
    filled = profile.filled_variable_count()
    if filled >= 8 and status:
        return "high"
    if filled >= 3:
        return "moderate"
    return "low"
