from __future__ import annotations

from src.knowledge.retriever import HybridRetriever, RetrievedChunk
from src.models.schemas import (
    Evidence,
    ImpactedMetric,
    LandProfile,
    Recommendation,
    RecommendationPack,
)
from src.reasoning.causal import infer_chains
from src.reasoning.diagnosis import diagnose, limiting_factors, overall_confidence


def _profile_query(profile: LandProfile, extra: str = "") -> str:
    bits = [extra] if extra else []
    if profile.soil.organic_carbon_pct is not None:
        bits.append(f"soil organic carbon {profile.soil.organic_carbon_pct}%")
    if profile.soil.ph is not None:
        bits.append(f"soil pH {profile.soil.ph}")
    if profile.climate.rainfall:
        bits.append(f"{profile.climate.rainfall} rainfall")
    if profile.land_use.crop:
        bits.append(profile.land_use.crop)
    if profile.land_use.management:
        bits.append(profile.land_use.management)
    if profile.land_use.type:
        bits.append(profile.land_use.type)
    if profile.geo.region:
        bits.append(profile.geo.region)
    if profile.human_impact.deforestation:
        bits.append(f"deforestation {profile.human_impact.deforestation}")
    bits.append("biodiversity restoration soil water habitat")
    return " ".join(bits)


def _score_intervention(item: dict, limiting: list[str], profile: LandProfile) -> float:
    score = 0.0
    addresses = " ".join(item.get("addresses", []))
    for factor in limiting:
        tokens = factor.lower().replace("/", " ").split()
        if any(token in addresses.replace("_", " ") for token in tokens if len(token) > 3):
            score += 3.0
    score += min(len(item.get("effects", [])), 4)
    score += {"high": 1.5, "moderate": 0.8, "low": 0.2}.get(item.get("confidence", "moderate"), 0.8)
    rainfall = (profile.climate.rainfall or "").lower()
    if rainfall in {"arid", "semi-arid"} and item["id"] in {
        "residue_mulch_microcatchments",
        "fmnr",
        "agroforestry_intercrop",
    }:
        score += 2.0
    if (profile.land_use.management or "").lower() == "monoculture" and item["id"] in {
        "diversified_intercropping",
        "legume_cover_crops",
        "pollinator_strips",
    }:
        score += 1.5
    if profile.soil.organic_carbon_pct is not None and profile.soil.organic_carbon_pct < 0.6:
        if item["id"] in {"organic_amendments", "legume_cover_crops", "residue_mulch_microcatchments"}:
            score += 1.5
    score += 0.4 * len(set(item.get("addresses", [])))
    return score


def _evidence_for(item: dict, chunks: list[RetrievedChunk]) -> list[Evidence]:
    evidence = []
    for cite in item.get("citations", []):
        evidence.append(
            Evidence(
                source=cite.get("source", ""),
                year=cite.get("year"),
                citation=cite.get("citation", ""),
                snippet=cite.get("snippet", ""),
                relevance=0.95,
                doc_id=item["id"],
            )
        )
    keywords = set(item.get("addresses", []) + [item["id"], item["title"].lower()])
    for chunk in chunks:
        hay = (chunk.text + " " + chunk.title).lower().replace("-", " ")
        if any(str(k).replace("_", " ") in hay for k in keywords):
            evidence.append(chunk.to_evidence())
        if len(evidence) >= 4:
            break
    return evidence[:4]


def recommend(profile: LandProfile, retriever: HybridRetriever, query_text: str = "") -> RecommendationPack:
    status = diagnose(profile)
    limiting = limiting_factors(status)
    chunks = retriever.search(_profile_query(profile, query_text), k=8)
    candidates = retriever.applicable_interventions(profile)
    ranked = sorted(
        candidates,
        key=lambda item: _score_intervention(item, limiting, profile),
        reverse=True,
    )

    picked: list[dict] = []
    families = set()
    for item in ranked:
        family = item["id"].split("_")[0]
        if family in families and len(picked) < 2:
            continue
        families.add(family)
        picked.append(item)
        if len(picked) == 3:
            break

    recs: list[Recommendation] = []
    for item in picked:
        impacts = [
            ImpactedMetric(
                metric=effect["metric"],
                direction=effect["direction"],
                expected_change=effect["expected_change"],
                mechanism=effect["mechanism"],
            )
            for effect in item.get("effects", [])
        ]
        recs.append(
            Recommendation(
                title=item["title"],
                action=item["action"],
                why_it_works=item["why"],
                impacted_metrics=impacts,
                time_horizon=item.get("time_horizon", "medium"),
                confidence=item.get("confidence", "moderate"),
                evidence=_evidence_for(item, chunks),
                synergies=item.get("synergies", []),
                caveats=item.get("caveats", []),
                addresses_limiting_factors=[
                    factor
                    for factor in limiting
                    if any(token in " ".join(item.get("addresses", [])).replace("_", " ") for token in factor.lower().split() if len(token) > 3)
                ],
            )
        )

    variables = []
    dumped = profile.as_context_dict()
    for group, payload in dumped.items():
        if isinstance(payload, dict):
            variables.extend([f"{group}.{key}" for key in payload if key != "notes"])
    if len(variables) < 3:
        variables = list(dict.fromkeys(variables + ["soil.organic_carbon_pct", "climate.rainfall", "land_use.management"]))

    diagnosis_bits = [item.rationale for item in status[:3]]
    if not diagnosis_bits:
        diagnosis_bits = [
            "Insufficient quantitative data; recommendations stay conservative and emphasize measurement of SOC, rainfall regime, and land use."
        ]
    diagnosis = (
        "Multi-metric diagnosis: "
        + " ".join(diagnosis_bits)
        + (
            f" Binding constraints: {', '.join(limiting)}."
            if limiting
            else " No critical red flags; protect existing function and add heterogeneity."
        )
    )

    return RecommendationPack(
        diagnosis_summary=diagnosis,
        limiting_factors=limiting or ["incomplete site data"],
        metric_status=status,
        causal_chains=infer_chains(profile, limiting),
        recommendations=recs,
        retrieved_evidence=[chunk.to_evidence() for chunk in chunks[:6]],
        confidence_overall=overall_confidence(profile, status),
        variables_used=variables,
        retrieval_notes=(
            f"Hybrid RAG fused LSA vectors + BM25 across {len(retriever.records)} indexed chunks; "
            f"structured filter kept {len(candidates)} candidate interventions before ranking."
        ),
    )
