import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from groundshift.api.app import create_app

    results_dir = tmp_path_factory.mktemp("emerging")
    coffee_data = {
        "crop_id": "coffee",
        "region": "ethiopia",
        "zones": [
            {"scenario": "ssp245", "horizon_year": 2040, "cell_count": 87, "confidence": "low"},
            {"scenario": "ssp585", "horizon_year": 2100, "cell_count": 38, "confidence": "low"},
        ],
    }
    (results_dir / "coffee_ethiopia.json").write_text(json.dumps(coffee_data))
    return TestClient(create_app(results_dir=results_dir))


class TestEmergingEndpoint:
    def test_known_crop_with_results_returns_200(self, client):
        r = client.get("/api/v1/crops/coffee/emerging")
        assert r.status_code == 200

    def test_unknown_crop_returns_404(self, client):
        r = client.get("/api/v1/crops/no_such_crop_xyz/emerging")
        assert r.status_code == 404

    def test_response_has_crop_id(self, client):
        r = client.get("/api/v1/crops/coffee/emerging")
        assert r.json()["crop_id"] == "coffee"

    def test_response_has_emerging_zones_list(self, client):
        r = client.get("/api/v1/crops/coffee/emerging")
        assert isinstance(r.json()["emerging_zones"], list)

    def test_zones_include_scenario_and_horizon(self, client):
        r = client.get("/api/v1/crops/coffee/emerging")
        zone = r.json()["emerging_zones"][0]
        assert "scenario" in zone
        assert "horizon_year" in zone

    def test_zones_include_cell_count_and_confidence(self, client):
        r = client.get("/api/v1/crops/coffee/emerging")
        zone = r.json()["emerging_zones"][0]
        assert "cell_count" in zone
        assert "confidence" in zone

    def test_zones_include_region(self, client):
        r = client.get("/api/v1/crops/coffee/emerging")
        zone = r.json()["emerging_zones"][0]
        assert "region" in zone
        assert zone["region"] == "ethiopia"

    def test_cell_count_is_integer(self, client):
        r = client.get("/api/v1/crops/coffee/emerging")
        assert isinstance(r.json()["emerging_zones"][0]["cell_count"], int)

    def test_correct_zone_count_from_file(self, client):
        r = client.get("/api/v1/crops/coffee/emerging")
        assert len(r.json()["emerging_zones"]) == 2

    def test_region_filter_returns_matching_zones(self, client):
        r = client.get("/api/v1/crops/coffee/emerging?region=ethiopia")
        assert r.status_code == 200
        for zone in r.json()["emerging_zones"]:
            assert zone["region"] == "ethiopia"

    def test_region_filter_unknown_region_returns_404(self, client):
        r = client.get("/api/v1/crops/coffee/emerging?region=no_such_region")
        assert r.status_code == 404
