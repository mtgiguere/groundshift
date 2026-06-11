import json

import pytest
from fastapi.testclient import TestClient


def _make_result(crop_id, region, zone_count=2):
    return {
        "crop_id": crop_id,
        "region": region,
        "zones": [
            {"scenario": "ssp245", "horizon_year": 2040, "cell_count": 50, "confidence": "low"}
        ]
        * zone_count,
    }


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from groundshift.api.app import create_app

    results_dir = tmp_path_factory.mktemp("runs")
    (results_dir / "coffee_ethiopia.json").write_text(
        json.dumps(_make_result("coffee", "ethiopia", zone_count=2))
    )
    (results_dir / "coffee_colombia.json").write_text(
        json.dumps(_make_result("coffee", "colombia", zone_count=3))
    )
    (results_dir / "tea_india.json").write_text(
        json.dumps(_make_result("tea", "india", zone_count=1))
    )
    return TestClient(create_app(results_dir=results_dir))


@pytest.fixture(scope="module")
def empty_client(tmp_path_factory):
    from groundshift.api.app import create_app

    results_dir = tmp_path_factory.mktemp("runs_empty")
    return TestClient(create_app(results_dir=results_dir))


class TestRunsEndpoint:
    def test_returns_200(self, client):
        r = client.get("/api/v1/runs")
        assert r.status_code == 200

    def test_empty_results_dir_returns_200(self, empty_client):
        r = empty_client.get("/api/v1/runs")
        assert r.status_code == 200

    def test_response_has_runs_list(self, client):
        r = client.get("/api/v1/runs")
        assert isinstance(r.json()["runs"], list)

    def test_response_has_total(self, client):
        r = client.get("/api/v1/runs")
        assert "total" in r.json()

    def test_total_matches_file_count(self, client):
        r = client.get("/api/v1/runs")
        data = r.json()
        assert data["total"] == len(data["runs"])

    def test_all_three_files_listed(self, client):
        r = client.get("/api/v1/runs")
        assert r.json()["total"] == 3

    def test_empty_dir_has_zero_total(self, empty_client):
        r = empty_client.get("/api/v1/runs")
        assert r.json()["total"] == 0

    def test_run_has_crop_id(self, client):
        r = client.get("/api/v1/runs")
        assert "crop_id" in r.json()["runs"][0]

    def test_run_has_region_id(self, client):
        r = client.get("/api/v1/runs")
        assert "region_id" in r.json()["runs"][0]

    def test_run_has_zone_count(self, client):
        r = client.get("/api/v1/runs")
        assert "zone_count" in r.json()["runs"][0]

    def test_zone_count_matches_zones_in_file(self, client):
        r = client.get("/api/v1/runs")
        runs = {(x["crop_id"], x["region_id"]): x for x in r.json()["runs"]}
        assert runs[("coffee", "ethiopia")]["zone_count"] == 2
        assert runs[("coffee", "colombia")]["zone_count"] == 3
        assert runs[("tea", "india")]["zone_count"] == 1

    def test_filter_by_crop_id(self, client):
        r = client.get("/api/v1/runs?crop_id=coffee")
        assert r.status_code == 200
        runs = r.json()["runs"]
        assert all(x["crop_id"] == "coffee" for x in runs)
        assert len(runs) == 2

    def test_filter_by_region_id(self, client):
        r = client.get("/api/v1/runs?region_id=ethiopia")
        assert r.status_code == 200
        runs = r.json()["runs"]
        assert all(x["region_id"] == "ethiopia" for x in runs)
        assert len(runs) == 1

    def test_filter_by_crop_and_region(self, client):
        r = client.get("/api/v1/runs?crop_id=coffee&region_id=colombia")
        assert r.status_code == 200
        runs = r.json()["runs"]
        assert len(runs) == 1
        assert runs[0]["crop_id"] == "coffee"
        assert runs[0]["region_id"] == "colombia"

    def test_filter_no_match_returns_empty_list(self, client):
        r = client.get("/api/v1/runs?crop_id=no_such_crop")
        assert r.status_code == 200
        assert r.json()["runs"] == []
        assert r.json()["total"] == 0
