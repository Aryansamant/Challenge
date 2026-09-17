from src.conversation.extractor import extract_from_text
from src.engine import BioIntelEngine
from src.models.schemas import ChatRequest, LandProfile
from src.reasoning.diagnosis import diagnose, limiting_factors


def test_low_soc_semi_arid_is_critical():
    profile = extract_from_text(
        "Soil organic carbon: 0.3%\nRainfall: low\nCrop: monoculture wheat\nRegion: semi-arid",
        LandProfile(),
    )
    status = diagnose(profile)
    soc = next(item for item in status if item.metric == "soil organic carbon")
    assert soc.severity == "critical"
    factors = limiting_factors(status)
    assert any("organic carbon" in f for f in factors)
    assert any("land use" in f or "habitat" in f for f in factors)


def test_engine_returns_grounded_multi_metric_pack():
    engine = BioIntelEngine()
    response = engine.respond(
        ChatRequest(
            message="Soil organic carbon: 0.3%\nRainfall: low\nCrop: monoculture wheat\nRegion: semi-arid"
        )
    )
    pack = response.pack
    assert pack is not None
    assert not response.needs_more_input
    assert len(pack.recommendations) >= 2
    assert len(pack.variables_used) >= 3
    assert pack.causal_chains
    assert pack.retrieved_evidence

    titles = " ".join(rec.title.lower() for rec in pack.recommendations)
    assert any(
        token in titles
        for token in ("agroforest", "intercrop", "cover", "mulch", "diversif", "micro-catch")
    )

    for rec in pack.recommendations:
        assert rec.action
        assert rec.why_it_works
        assert rec.impacted_metrics
        assert rec.time_horizon in {"short", "medium", "long"}
        assert rec.evidence
        assert len(rec.impacted_metrics) >= 1
        joined = " ".join(m.metric.lower() for m in rec.impacted_metrics)
        # each rec should speak to more than a slogan
        assert "sustainable" not in rec.action.lower() or rec.evidence

    # at least one recommendation couples soil + biodiversity/habitat
    coupled = False
    for rec in pack.recommendations:
        metrics = " ".join(m.metric.lower() for m in rec.impacted_metrics)
        if "carbon" in metrics and (
            "species" in metrics or "habitat" in metrics or "microbial" in metrics or "pollinator" in metrics
        ):
            coupled = True
    assert coupled
    assert "FAO" in response.assistant_message or "Poeplau" in response.assistant_message or "IPCC" in response.assistant_message


def test_engine_asks_before_preaching():
    engine = BioIntelEngine()
    response = engine.respond(ChatRequest(message="Biodiversity is declining on my land"))
    assert response.needs_more_input
    assert response.pack and response.pack.follow_ups
    assert "organic carbon" in response.assistant_message.lower()
