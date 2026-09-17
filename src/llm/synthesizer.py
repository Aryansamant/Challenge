from __future__ import annotations

from src.config import settings
from src.models.schemas import LandProfile, RecommendationPack


def _horizon_label(value: str) -> str:
    return {"short": "short term (0–2 years)", "medium": "medium term (2–6 years)", "long": "long term (6–15 years)"}.get(
        value, value
    )


def render_pack(pack: RecommendationPack, profile: LandProfile, questions_only: bool = False) -> str:
    lines: list[str] = []
    if questions_only and pack.follow_ups:
        lines.append("I can reason like a field scientist here, but three coupled variables are still missing.")
        lines.append("Please fill these gaps so the recommendation is site-specific rather than generic:")
        for follow in pack.follow_ups:
            lines.append(f"- {follow.question} _{follow.why_needed}_")
        if pack.recommendations:
            lines.append("\nA cautious, low-confidence sketch based on what you already shared:")
        else:
            return "\n".join(lines)

    lines.append(f"**Diagnosis.** {pack.diagnosis_summary}")
    if pack.limiting_factors:
        lines.append("**Limiting factors:** " + "; ".join(pack.limiting_factors) + ".")
    if pack.causal_chains:
        lines.append("**Coupled mechanisms (not single-variable):**")
        for chain in pack.causal_chains:
            lines.append(f"- {' → '.join(chain.path)} — {chain.explanation}")

    for idx, rec in enumerate(pack.recommendations, 1):
        metrics = ", ".join(f"{m.metric} ({m.direction}: {m.expected_change})" for m in rec.impacted_metrics)
        cite = rec.evidence[0].citation if rec.evidence else "see retrieved corpus"
        lines.append(
            f"\n**Recommendation {idx}: {rec.title}**  \n"
            f"- **What to do:** {rec.action}  \n"
            f"- **Why it works:** {rec.why_it_works}  \n"
            f"- **Impacted metrics:** {metrics}  \n"
            f"- **Time horizon:** {_horizon_label(rec.time_horizon)}  \n"
            f"- **Confidence:** {rec.confidence}  \n"
            f"- **Evidence:** {cite}"
        )
        if rec.caveats:
            lines.append(f"- **Caveat:** {rec.caveats[0]}")

    used = ", ".join(pack.variables_used[:8]) or "limited"
    lines.append(
        f"\nOverall confidence: **{pack.confidence_overall}** "
        f"(variables used: {used}). {pack.retrieval_notes}"
    )
    region = profile.geo.region or profile.climate.climate_zone
    if region:
        lines.append(f"Spatial context: {region}.")
    return "\n".join(lines)


def maybe_llm_polish(markdown: str, pack: RecommendationPack) -> str:
    """Optional phrasing only. The pack remains the source of truth."""
    if not settings.llm_api_key:
        return markdown
    try:
        import httpx

        prompt = (
            "You are an environmental scientist. Rewrite the notes more fluently but do NOT add new practices, "
            "numbers, or citations that are not already present. Keep headings and the recommendation structure. "
            "If something is missing, leave it missing.\n\n"
            f"{markdown}"
        )
        response = httpx.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": "Stay strictly grounded in the provided scientific notes."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        return text.strip() or markdown
    except Exception:
        return markdown
