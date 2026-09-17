from __future__ import annotations

from src.knowledge.store import causal_graph
from src.models.schemas import CausalChain, LandProfile


METRIC_ALIASES = {
    "soil_organic_carbon": "soil organic carbon",
    "soil_ph": "soil pH",
    "soil_moisture": "soil moisture",
    "microbial_diversity": "microbial diversity",
    "nutrient_cycling": "nutrient cycling",
    "plant_diversity": "plant diversity",
    "habitat_heterogeneity": "habitat heterogeneity",
    "species_richness": "species richness",
    "pollinators": "pollinators",
    "rainfall": "rainfall",
    "temperature_extremes": "temperature extremes",
    "fragmentation": "habitat fragmentation",
    "pesticide_load": "pesticide load",
    "deforestation": "deforestation",
    "erosion": "erosion",
    "water_infiltration": "water infiltration",
    "microclimate": "microclimate",
}


def _active_nodes(profile: LandProfile) -> list[str]:
    nodes = []
    if profile.soil.organic_carbon_pct is not None:
        nodes.append("soil_organic_carbon")
    if profile.soil.ph is not None:
        nodes.append("soil_ph")
    if profile.soil.moisture or profile.climate.rainfall:
        nodes.append("soil_moisture")
        nodes.append("rainfall")
    if profile.soil.erosion:
        nodes.append("erosion")
    if profile.land_use.management or profile.land_use.type:
        nodes.append("plant_diversity")
        nodes.append("habitat_heterogeneity")
    if profile.biodiversity.species_richness or profile.biodiversity.pollinator_status:
        nodes.append("species_richness")
        nodes.append("pollinators")
    if profile.human_impact.fragmentation:
        nodes.append("fragmentation")
    if profile.human_impact.deforestation:
        nodes.append("deforestation")
    if profile.human_impact.pesticide_intensity:
        nodes.append("pesticide_load")
    if profile.climate.temperature or profile.climate.drought_risk:
        nodes.append("temperature_extremes")
    if len(nodes) < 3:
        nodes.extend(["soil_organic_carbon", "rainfall", "habitat_heterogeneity"])
    # unique preserve order
    seen = []
    for node in nodes:
        if node not in seen:
            seen.append(node)
    return seen


def infer_chains(profile: LandProfile, limiting: list[str], limit: int = 4) -> list[CausalChain]:
    graph = causal_graph()
    edges = graph["edges"]
    active = set(_active_nodes(profile))
    limiting_l = {item.lower() for item in limiting}

    def involved(edge: dict) -> bool:
        labels = {edge["from"].replace("_", " "), edge["to"].replace("_", " ")}
        if any(any(word in token for word in labels) for token in limiting_l):
            return True
        return edge["from"] in active and edge["to"] in active

    ranked = [edge for edge in edges if involved(edge)]
    if not ranked:
        ranked = edges[:limit]

    chains: list[CausalChain] = []
    used = set()
    for edge in ranked:
        key = (edge["from"], edge["to"])
        if key in used:
            continue
        used.add(key)
        left = METRIC_ALIASES.get(edge["from"], edge["from"])
        right = METRIC_ALIASES.get(edge["to"], edge["to"])
        sign = {"+": "increases", "-": "reduces", "~": "reshapes"}.get(edge["sign"], "affects")
        source = edge["sources"][0] if edge.get("sources") else "internal causal graph"
        chains.append(
            CausalChain(
                path=[left, right],
                explanation=f"{left.capitalize()} {sign} {right}: {edge['mechanism']} ({source})",
            )
        )
        if len(chains) >= limit:
            break
    return chains
