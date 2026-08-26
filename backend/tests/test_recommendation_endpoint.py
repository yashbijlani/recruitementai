import pytest

try:
    from fastapi.testclient import TestClient
    from app.main import app
except Exception as error:
    pytest.skip(f"PostgreSQL integration test requires a running database: {error}", allow_module_level=True)


def test_industry_phrase_is_not_parsed_as_location():
    response = TestClient(app).post("/api/recommendations", json={"query": "Find project managers in the IT industry with 5+ years experience", "limit": 3})
    assert response.status_code == 200
    parsed = response.json()["parsed_requirements"]
    assert parsed["industry"] == "technology"
    assert parsed["location"] is None


def test_recommendation_contract_is_local_and_explainable():
    response = TestClient(app).post("/api/recommendations", json={"query": "Find candidates in Bangalore with salary below 15 LPA", "limit": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]
    assert isinstance(payload["parsed_requirements"], dict)
    for result in payload["results"]:
        assert set(result["score_breakdown"]) == {"position", "experience", "industry", "location", "salary", "notice"}
        assert result["explanation"]
