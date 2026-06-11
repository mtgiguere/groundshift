import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from groundshift.api.app import create_app

    return TestClient(create_app())


class TestRegionsList:
    def test_returns_200(self, client):
        r = client.get("/api/v1/regions")
        assert r.status_code == 200

    def test_response_has_regions_key(self, client):
        r = client.get("/api/v1/regions")
        assert "regions" in r.json()

    def test_regions_is_list(self, client):
        r = client.get("/api/v1/regions")
        assert isinstance(r.json()["regions"], list)

    def test_each_region_has_id_and_name(self, client):
        r = client.get("/api/v1/regions")
        for region in r.json()["regions"]:
            assert "id" in region
            assert "name" in region

    def test_each_region_has_bbox(self, client):
        r = client.get("/api/v1/regions")
        for region in r.json()["regions"]:
            assert "bbox" in region

    def test_bbox_has_four_bounds(self, client):
        r = client.get("/api/v1/regions")
        bbox = r.json()["regions"][0]["bbox"]
        for key in ("min_lon", "min_lat", "max_lon", "max_lat"):
            assert key in bbox

    def test_total_matches_list_length(self, client):
        r = client.get("/api/v1/regions")
        data = r.json()
        assert data["total"] == len(data["regions"])

    def test_ethiopia_is_in_list(self, client):
        r = client.get("/api/v1/regions")
        ids = [reg["id"] for reg in r.json()["regions"]]
        assert "ethiopia" in ids


class TestRegionDetail:
    def test_known_region_returns_200(self, client):
        r = client.get("/api/v1/regions/ethiopia")
        assert r.status_code == 200

    def test_unknown_region_returns_404(self, client):
        r = client.get("/api/v1/regions/no_such_region_xyz")
        assert r.status_code == 404

    def test_response_id_matches_path(self, client):
        r = client.get("/api/v1/regions/ethiopia")
        assert r.json()["id"] == "ethiopia"

    def test_response_has_name(self, client):
        r = client.get("/api/v1/regions/ethiopia")
        assert "name" in r.json()

    def test_response_has_bbox(self, client):
        r = client.get("/api/v1/regions/ethiopia")
        assert "bbox" in r.json()

    def test_ethiopia_bbox_bounds_are_plausible(self, client):
        r = client.get("/api/v1/regions/ethiopia")
        bbox = r.json()["bbox"]
        assert bbox["min_lon"] < bbox["max_lon"]
        assert bbox["min_lat"] < bbox["max_lat"]
        # Ethiopia is roughly 33–48°E, 3–15°N
        assert 30.0 <= bbox["min_lon"] <= 40.0
        assert 0.0 <= bbox["min_lat"] <= 6.0
