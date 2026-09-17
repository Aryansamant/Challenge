from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_and_structured_assess():
    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["chunks"] > 0
    assert body["interventions"] >= 10

    res = client.post(
        "/api/assess",
        json={
            "soil": {"organic_carbon_pct": 0.3},
            "climate": {"rainfall": "semi-arid"},
            "land_use": {"type": "cropland", "crop": "wheat", "management": "monoculture"},
            "geo": {"region": "semi-arid"},
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["pack"]["recommendations"]
    assert payload["retrieved_doc_ids"]
    assert payload["pack"]["causal_chains"]
