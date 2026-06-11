import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from groundshift.api.app import create_app

    return TestClient(create_app())


class TestCropsList:
    def test_returns_200(self, client):
        r = client.get("/api/v1/crops")
        assert r.status_code == 200

    def test_response_has_crops_key(self, client):
        r = client.get("/api/v1/crops")
        assert "crops" in r.json()

    def test_crops_is_list(self, client):
        r = client.get("/api/v1/crops")
        assert isinstance(r.json()["crops"], list)

    def test_each_crop_has_id_and_name(self, client):
        r = client.get("/api/v1/crops")
        for crop in r.json()["crops"]:
            assert "id" in crop
            assert "name" in crop

    def test_total_matches_list_length(self, client):
        r = client.get("/api/v1/crops")
        data = r.json()
        assert data["total"] == len(data["crops"])

    def test_coffee_is_in_list(self, client):
        r = client.get("/api/v1/crops")
        ids = [c["id"] for c in r.json()["crops"]]
        assert "coffee" in ids


class TestCropDetail:
    def test_known_crop_returns_200(self, client):
        r = client.get("/api/v1/crops/coffee")
        assert r.status_code == 200

    def test_unknown_crop_returns_404(self, client):
        r = client.get("/api/v1/crops/no_such_crop_xyz")
        assert r.status_code == 404

    def test_response_id_matches_path(self, client):
        r = client.get("/api/v1/crops/coffee")
        assert r.json()["id"] == "coffee"

    def test_response_has_name(self, client):
        r = client.get("/api/v1/crops/coffee")
        assert "name" in r.json()

    def test_response_has_climate_envelope(self, client):
        r = client.get("/api/v1/crops/coffee")
        assert "climate_envelope" in r.json()

    def test_climate_envelope_has_thresholds(self, client):
        r = client.get("/api/v1/crops/coffee")
        envelope = r.json()["climate_envelope"]
        assert "thresholds" in envelope

    def test_temperature_threshold_has_four_bounds(self, client):
        r = client.get("/api/v1/crops/coffee")
        temp = r.json()["climate_envelope"]["thresholds"]["mean_annual_temp_c"]
        for key in ("viable_min", "optimal_min", "optimal_max", "viable_max"):
            assert key in temp
