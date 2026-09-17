from src.conversation.dialogue import needed_questions, ready_to_recommend
from src.conversation.extractor import extract_from_text, merge_profiles
from src.models.schemas import LandProfile


def test_extracts_hackathon_example_text():
    profile = extract_from_text(
        "Soil organic carbon: 0.3%\nRainfall: low\nCrop: monoculture wheat\nRegion: semi-arid",
        LandProfile(),
    )
    assert profile.soil.organic_carbon_pct == 0.3
    assert profile.climate.rainfall == "semi-arid"
    assert profile.land_use.crop == "wheat"
    assert profile.land_use.management == "monoculture"
    assert profile.geo.region == "semi-arid"
    assert ready_to_recommend(profile)


def test_extracts_flat_json():
    profile = extract_from_text(
        '{"soil_organic_carbon": 0.3, "rainfall": "low", "crop": "monoculture wheat", "region": "semi-arid"}',
        LandProfile(),
    )
    assert profile.soil.organic_carbon_pct == 0.3
    assert profile.climate.rainfall == "semi-arid"
    assert profile.land_use.management == "monoculture"
    assert ready_to_recommend(profile)


def test_incomplete_prompt_asks_for_three_axes():
    profile = extract_from_text("Biodiversity is declining on my land", LandProfile())
    assert not ready_to_recommend(profile)
    questions = needed_questions(profile)
    slots = {q.slot for q in questions}
    assert "soil.organic_carbon_pct" in slots
    assert "climate.rainfall" in slots
    assert "land_use.management" in slots


def test_memory_merges_across_turns():
    first = extract_from_text("SOC is 0.3%", LandProfile())
    second = extract_from_text("Rainfall is semi-arid, monoculture wheat", first)
    merged = merge_profiles(first, second)
    assert merged.soil.organic_carbon_pct == 0.3
    assert merged.climate.rainfall == "semi-arid"
    assert merged.land_use.crop == "wheat"
